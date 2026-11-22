"""Unit tests for the News API.

Run them with:  python manage.py test
The email and the /api/approved/ POST are mocked so nothing real is sent.
"""
from unittest.mock import patch

from django.core import mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import CustomUser, Publisher, Article, Newsletter


def make_user(username, role):
    """Makes a user with a role and an email."""
    return CustomUser.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='TestPass123!',
        role=role,
    )


def make_article(title, author, publisher=None, approved=False):
    """Makes an article for the tests.

    update() skips the signal, so setting up approved articles here
    doesn't send any emails or API posts.
    """
    article = Article.objects.create(
        title=title, content='Text', author=author, publisher=publisher,
    )
    if approved:
        Article.objects.filter(id=article.id).update(approved=True)
        article.refresh_from_db()
    return article


class NewsAPITestCase(APITestCase):
    """Sets up users, a publisher and some articles for every test."""

    def setUp(self):
        """Makes the test data."""
        self.reader = make_user('reader', CustomUser.READER)
        self.other_reader = make_user('reader2', CustomUser.READER)
        self.editor = make_user('editor', CustomUser.EDITOR)
        self.other_editor = make_user('editor2', CustomUser.EDITOR)
        self.journalist = make_user('journalist', CustomUser.JOURNALIST)
        self.other_journalist = make_user('journalist2', CustomUser.JOURNALIST)

        self.owner = make_user('owner', CustomUser.PUBLISHER)
        self.other_owner = make_user('owner2', CustomUser.PUBLISHER)

        self.publisher = Publisher.objects.create(
            name='Daily News', owner=self.owner,
        )
        self.publisher.editors.add(self.editor)
        self.publisher.journalists.add(self.journalist)
        self.other_publisher = Publisher.objects.create(
            name='Other Times', owner=self.other_owner,
        )
        self.other_publisher.editors.add(self.other_editor)

        # approved articles
        self.publisher_article = make_article(
            'Publisher story', self.journalist, self.publisher, approved=True,
        )
        self.independent_article = make_article(
            'Independent story', self.other_journalist, approved=True,
        )
        self.other_publisher_article = make_article(
            'Other publisher story', self.other_journalist,
            self.other_publisher, approved=True,
        )
        # not approved yet
        self.pending_article = make_article(
            'Pending story', self.journalist, self.publisher,
        )
        # independent and not published yet
        self.draft_article = make_article('Draft story', self.journalist)

        # the reader follows Daily News and journalist2
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.other_journalist)

    def login(self, user):
        """Logs in with a token, like a real API client would."""
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')


class AuthenticationTests(NewsAPITestCase):
    """Tests for logging in and getting a token."""

    def test_get_token_with_right_password(self):
        response = self.client.post('/api/token/', {
            'username': 'reader', 'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_get_token_with_wrong_password_fails(self):
        response = self.client.post('/api/token/', {
            'username': 'reader', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_logged_in_is_blocked(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_every_role_can_list_articles(self):
        for user in [self.reader, self.editor, self.journalist]:
            self.login(user)
            response = self.client.get('/api/articles/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class RoleAndGroupTests(NewsAPITestCase):
    """Tests that roles put users in the right group."""

    def test_users_are_in_their_role_group(self):
        self.assertTrue(self.reader.groups.filter(name='Reader').exists())
        self.assertTrue(self.editor.groups.filter(name='Editor').exists())
        self.assertTrue(
            self.journalist.groups.filter(name='Journalist').exists()
        )
        self.assertTrue(self.owner.groups.filter(name='Publisher').exists())

    def test_journalist_has_no_subscriptions(self):
        # a reader who becomes a journalist loses their subscriptions
        self.reader.role = CustomUser.JOURNALIST
        self.reader.save()
        self.assertEqual(self.reader.subscribed_publishers.count(), 0)
        self.assertEqual(self.reader.subscribed_journalists.count(), 0)
        self.assertTrue(
            self.reader.groups.filter(name='Journalist').exists()
        )


class ReaderTests(NewsAPITestCase):
    """Tests for what readers can and can't do."""

    def test_list_only_shows_approved_articles(self):
        self.login(self.reader)
        response = self.client.get('/api/articles/')
        titles = [article['title'] for article in response.data]
        self.assertEqual(len(titles), 3)
        self.assertNotIn('Pending story', titles)

    def test_subscribed_only_shows_followed_content(self):
        self.login(self.reader)
        response = self.client.get('/api/articles/subscribed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = sorted(article['title'] for article in response.data)
        # Daily News article + both of journalist2's articles
        self.assertEqual(titles, [
            'Independent story',
            'Other publisher story',
            'Publisher story',
        ])
        self.assertNotIn('Pending story', titles)

    def test_reader_with_no_subscriptions_gets_nothing(self):
        self.login(self.other_reader)
        response = self.client.get('/api/articles/subscribed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_only_readers_have_a_subscribed_feed(self):
        self.login(self.journalist)
        response = self.client.get('/api/articles/subscribed/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reader_can_get_one_approved_article(self):
        self.login(self.reader)
        response = self.client.get(
            f'/api/articles/{self.publisher_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Publisher story')

    def test_reader_cannot_see_pending_article(self):
        self.login(self.reader)
        response = self.client.get(
            f'/api/articles/{self.pending_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_article_gives_404(self):
        self.login(self.reader)
        response = self.client.get('/api/articles/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reader_cannot_create_update_or_delete(self):
        self.login(self.reader)
        url = f'/api/articles/{self.publisher_article.id}/'
        post = self.client.post(
            '/api/articles/', {'title': 'Hi', 'content': 'Text'}
        )
        put = self.client.put(url, {'title': 'Changed'})
        delete = self.client.delete(url)
        self.assertEqual(post.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(put.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            Article.objects.filter(id=self.publisher_article.id).exists()
        )

    def test_reader_cannot_approve(self):
        self.login(self.reader)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JournalistTests(NewsAPITestCase):
    """Tests for what journalists can and can't do."""

    def test_journalist_can_create_independent_article(self):
        self.login(self.journalist)
        response = self.client.post('/api/articles/', {
            'title': 'New story', 'content': 'Some text',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author']['username'], 'journalist')
        self.assertIsNone(response.data['publisher'])
        # new articles always wait for an editor
        self.assertFalse(response.data['approved'])

    def test_journalist_can_create_article_for_their_publisher(self):
        self.login(self.journalist)
        response = self.client.post('/api/articles/', {
            'title': 'New story', 'content': 'Some text',
            'publisher': self.publisher.id,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['publisher_name'], 'Daily News')

    def test_journalist_cannot_post_for_other_publisher(self):
        self.login(self.journalist)
        response = self.client.post('/api/articles/', {
            'title': 'New story', 'content': 'Some text',
            'publisher': self.other_publisher.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_cannot_approve_own_article_by_sending_it(self):
        self.login(self.journalist)
        response = self.client.post('/api/articles/', {
            'title': 'Sneaky', 'content': 'Text', 'approved': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['approved'])

    def test_missing_fields_give_400(self):
        self.login(self.journalist)
        response = self.client.post('/api/articles/', {'title': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_journalist_can_update_own_article(self):
        self.login(self.journalist)
        response = self.client.put(
            f'/api/articles/{self.publisher_article.id}/',
            {'title': 'Updated title'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.publisher_article.refresh_from_db()
        self.assertEqual(self.publisher_article.title, 'Updated title')

    def test_journalist_cannot_update_someone_elses_article(self):
        self.login(self.journalist)
        response = self.client.put(
            f'/api/articles/{self.independent_article.id}/',
            {'title': 'Hacked'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_can_delete_own_article(self):
        self.login(self.journalist)
        response = self.client.delete(
            f'/api/articles/{self.pending_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Article.objects.filter(id=self.pending_article.id).exists()
        )

    def test_journalist_can_see_own_pending_article(self):
        self.login(self.journalist)
        response = self.client.get(
            f'/api/articles/{self.pending_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_journalist_cannot_approve(self):
        self.login(self.journalist)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@patch('news.functions.notify.requests.post')
class EditorTests(NewsAPITestCase):
    """Tests for what editors can and can't do.

    requests.post is mocked for the whole class so the signal never
    makes a real web request.
    """

    def test_editor_can_approve(self, mock_post):
        mock_post.return_value.status_code = 201
        self.login(self.editor)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)

    def test_editor_of_other_publisher_cannot_approve(self, mock_post):
        self.login(self.other_editor)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending_article.refresh_from_db()
        self.assertFalse(self.pending_article.approved)

    def test_approving_twice_gives_400(self, mock_post):
        self.login(self.editor)
        response = self.client.post(
            f'/api/articles/{self.publisher_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_editor_can_update_own_publisher_article(self, mock_post):
        self.login(self.editor)
        response = self.client.put(
            f'/api/articles/{self.publisher_article.id}/',
            {'content': 'Fixed by the editor'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_editor_cannot_update_other_publisher_article(self, mock_post):
        self.login(self.editor)
        response = self.client.put(
            f'/api/articles/{self.other_publisher_article.id}/',
            {'content': 'Not my publisher'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_cannot_change_independent_article(self, mock_post):
        # independent articles have no editor
        self.login(self.editor)
        response = self.client.delete(
            f'/api/articles/{self.independent_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_cannot_approve_independent_article(self, mock_post):
        self.login(self.editor)
        response = self.client.post(
            f'/api/articles/{self.draft_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete(self, mock_post):
        self.login(self.editor)
        response = self.client.delete(
            f'/api/articles/{self.publisher_article.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Article.objects.filter(id=self.publisher_article.id).exists()
        )

    def test_editor_cannot_create_article(self, mock_post):
        self.login(self.editor)
        response = self.client.post('/api/articles/', {
            'title': 'Editor story', 'content': 'Text',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@patch('news.functions.notify.requests.post')
class PublishTests(NewsAPITestCase):
    """Tests that journalists publish their own independent articles."""

    def test_journalist_can_publish_own_independent_article(self, mock_post):
        mock_post.return_value.status_code = 201
        self.login(self.journalist)
        response = self.client.post(
            f'/api/articles/{self.draft_article.id}/publish/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.draft_article.refresh_from_db()
        self.assertTrue(self.draft_article.approved)

    def test_publishing_runs_the_signal(self, mock_post):
        mock_post.return_value.status_code = 201
        # reader2 follows the journalist, so they get the email
        self.other_reader.subscribed_journalists.add(self.journalist)
        self.login(self.journalist)
        self.client.post(f'/api/articles/{self.draft_article.id}/publish/')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].bcc, ['reader2@example.com'])
        mock_post.assert_called_once()

    def test_other_journalist_cannot_publish(self, mock_post):
        self.login(self.other_journalist)
        response = self.client.post(
            f'/api/articles/{self.draft_article.id}/publish/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_publish_publisher_article(self, mock_post):
        # publisher articles must be approved by an editor
        self.login(self.journalist)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/publish/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_publish_twice(self, mock_post):
        self.login(self.journalist)
        response = self.client.post(
            f'/api/articles/{self.publisher_article.id}/publish/'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reader_cannot_publish(self, mock_post):
        self.login(self.reader)
        response = self.client.post(
            f'/api/articles/{self.draft_article.id}/publish/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@patch('news.functions.notify.requests.post')
class ApprovalSignalTests(NewsAPITestCase):
    """Tests that approving sends the email and posts to /api/approved/."""

    def test_approval_emails_subscribers(self, mock_post):
        mock_post.return_value.status_code = 201
        self.login(self.editor)
        self.client.post(f'/api/articles/{self.pending_article.id}/approve/')

        # the email backend is swapped for a test one, so check the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Pending story', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].bcc, ['reader@example.com'])

    def test_approval_posts_to_approved_api(self, mock_post):
        mock_post.return_value.status_code = 201
        self.login(self.editor)
        self.client.post(f'/api/articles/{self.pending_article.id}/approve/')

        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        sent_data = mock_post.call_args.kwargs['json']
        self.assertTrue(url.endswith('/api/approved/'))
        self.assertEqual(sent_data['id'], self.pending_article.id)
        self.assertIn('Token', mock_post.call_args.kwargs['headers'][
            'Authorization'
        ])

    def test_no_email_or_post_when_not_approved(self, mock_post):
        # just editing an article should not send anything
        self.pending_article.title = 'Still pending'
        self.pending_article.save()
        self.assertEqual(len(mail.outbox), 0)
        mock_post.assert_not_called()

    def test_no_email_when_no_subscribers(self, mock_post):
        mock_post.return_value.status_code = 201
        self.reader.subscribed_publishers.clear()
        self.login(self.editor)
        self.client.post(f'/api/articles/{self.pending_article.id}/approve/')
        self.assertEqual(len(mail.outbox), 0)
        mock_post.assert_called_once()

    def test_api_being_down_does_not_break_approval(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError('down')
        self.login(self.editor)
        response = self.client.post(
            f'/api/articles/{self.pending_article.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending_article.refresh_from_db()
        self.assertTrue(self.pending_article.approved)


class ApprovedEndpointTests(NewsAPITestCase):
    """Tests for the /api/approved/ log endpoint itself."""

    def test_editor_can_log_approved_article(self):
        self.login(self.editor)
        response = self.client.post('/api/approved/', {
            'id': self.publisher_article.id,
            'title': 'Publisher story',
            'author': 'journalist',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_log_unapproved_article(self):
        self.login(self.editor)
        response = self.client.post('/api/approved/', {
            'id': self.pending_article.id,
            'title': 'Pending story',
            'author': 'journalist',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_journalist_can_log_published_article(self):
        self.login(self.journalist)
        response = self.client.post('/api/approved/', {
            'id': self.publisher_article.id,
            'title': 'Publisher story',
            'author': 'journalist',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reader_cannot_log(self):
        self.login(self.reader)
        response = self.client.post('/api/approved/', {
            'id': self.publisher_article.id,
            'title': 'Publisher story',
            'author': 'journalist',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class NewsletterTests(NewsAPITestCase):
    """Tests that newsletters work for each role."""

    def setUp(self):
        """Adds a newsletter by the journalist."""
        super().setUp()
        self.newsletter = Newsletter.objects.create(
            title='Weekly', description='Best of the week',
            author=self.journalist, publisher=self.publisher,
        )
        self.newsletter.articles.add(self.publisher_article)

    def test_reader_can_view_newsletters(self):
        self.login(self.reader)
        response = self.client.get('/api/newsletters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['title'], 'Weekly')
        self.assertEqual(
            response.data[0]['articles'], [self.publisher_article.id]
        )

    def test_reader_cannot_create_newsletter(self):
        self.login(self.reader)
        response = self.client.post('/api/newsletters/', {'title': 'Mine'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journalist_can_create_newsletter(self):
        self.login(self.journalist)
        response = self.client.post('/api/newsletters/', {
            'title': 'Monthly',
            'description': 'Monthly picks',
            'articles': [
                self.publisher_article.id, self.independent_article.id,
            ],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['articles']), 2)
        self.assertEqual(response.data['author']['username'], 'journalist')

    def test_journalist_cannot_use_other_publisher(self):
        self.login(self.journalist)
        response = self.client.post('/api/newsletters/', {
            'title': 'Wrong publisher',
            'publisher': self.other_publisher.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journalist_only_sees_own_newsletters(self):
        Newsletter.objects.create(
            title='Not mine', author=self.other_journalist,
        )
        self.login(self.journalist)
        response = self.client.get('/api/newsletters/')
        titles = [newsletter['title'] for newsletter in response.data]
        self.assertEqual(titles, ['Weekly'])

    def test_newsletter_cannot_have_pending_article(self):
        self.login(self.journalist)
        response = self.client.post('/api/newsletters/', {
            'title': 'Bad',
            'articles': [self.pending_article.id],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_editor_can_update_and_delete_newsletter(self):
        self.login(self.editor)
        url = f'/api/newsletters/{self.newsletter.id}/'
        put = self.client.put(url, {'title': 'Weekly (edited)'})
        self.assertEqual(put.status_code, status.HTTP_200_OK)
        self.assertEqual(put.data['title'], 'Weekly (edited)')
        delete = self.client.delete(url)
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Newsletter.objects.exists())

    def test_editor_of_other_publisher_cannot_change(self):
        self.login(self.other_editor)
        response = self.client.delete(
            f'/api/newsletters/{self.newsletter.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_journalist_cannot_change_newsletter(self):
        self.login(self.other_journalist)
        response = self.client.put(
            f'/api/newsletters/{self.newsletter.id}/', {'title': 'Mine now'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_cannot_create_newsletter(self):
        self.login(self.editor)
        response = self.client.post('/api/newsletters/', {'title': 'Ed'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PublisherTests(NewsAPITestCase):
    """Tests for the publisher list."""

    def test_reader_sees_all_publishers_with_staff(self):
        self.login(self.reader)
        response = self.client.get('/api/publishers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        daily = [p for p in response.data if p['name'] == 'Daily News'][0]
        self.assertEqual(daily['owner']['username'], 'owner')
        self.assertEqual(daily['editors'][0]['username'], 'editor')
        self.assertEqual(daily['journalists'][0]['username'], 'journalist')

    def test_editor_and_journalist_only_see_their_publishers(self):
        for user in [self.editor, self.journalist]:
            self.login(user)
            response = self.client.get('/api/publishers/')
            names = [publisher['name'] for publisher in response.data]
            self.assertEqual(names, ['Daily News'])


class PublisherAccountTests(NewsAPITestCase):
    """Tests for registering a publisher and adding staff (website)."""

    def register(self, **extra):
        """Sends the register form."""
        data = {
            'username': 'newowner',
            'email': 'newowner@example.com',
            'role': 'publisher',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        data.update(extra)
        return self.client.post('/register/', data)

    def test_registering_a_publisher_makes_the_publication(self):
        response = self.register(publication_name='Morning Post')
        self.assertRedirects(response, '/my-publication/')
        publication = Publisher.objects.get(name='Morning Post')
        self.assertEqual(publication.owner.username, 'newowner')

    def test_publisher_needs_a_publication_name(self):
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            CustomUser.objects.filter(username='newowner').exists()
        )

    def test_publication_name_must_be_new(self):
        self.register(publication_name='Daily News')
        self.assertFalse(
            CustomUser.objects.filter(username='newowner').exists()
        )

    def test_publisher_can_add_and_remove_staff(self):
        self.client.force_login(self.other_owner)
        self.client.post('/my-publication/', {
            'add_staff': '', 'username': 'journalist2',
        })
        self.assertTrue(
            self.other_publisher.journalists.filter(
                id=self.other_journalist.id
            ).exists()
        )
        self.client.post(
            f'/my-publication/remove/{self.other_journalist.id}/'
        )
        self.assertFalse(self.other_publisher.journalists.exists())

    def test_publisher_cannot_add_a_reader(self):
        self.client.force_login(self.owner)
        response = self.client.post('/my-publication/', {
            'add_staff': '', 'username': 'reader',
        })
        self.assertContains(response, 'only add editors and journalists')
        self.assertFalse(
            self.publisher.journalists.filter(id=self.reader.id).exists()
        )

    def test_only_publishers_can_open_my_publication(self):
        self.client.force_login(self.editor)
        response = self.client.get('/my-publication/')
        self.assertEqual(response.status_code, 403)

    def test_journalist_cannot_see_publisher_pages(self):
        self.client.force_login(self.journalist)
        response = self.client.get('/publishers/')
        self.assertEqual(response.status_code, 403)
