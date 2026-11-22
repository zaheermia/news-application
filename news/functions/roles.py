"""Helper functions for roles, groups and who is allowed to do what."""
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

# the permissions each role's group gets (from the task)
GROUP_PERMISSIONS = {
    'Reader': [
        'view_article', 'view_newsletter', 'view_publisher',
    ],
    'Editor': [
        'view_article', 'change_article', 'delete_article',
        'approve_article',
        'view_newsletter', 'change_newsletter', 'delete_newsletter',
        'view_publisher',
    ],
    'Journalist': [
        'add_article', 'view_article', 'change_article', 'delete_article',
        'add_newsletter', 'view_newsletter', 'change_newsletter',
        'delete_newsletter',
        'view_publisher',
    ],
    # the publisher account runs its publication and its staff
    'Publisher': [
        'view_article', 'view_newsletter',
        'view_publisher', 'change_publisher',
    ],
}


def get_group(name):
    """Gets a role's group and gives it its permissions if it has none."""
    group, created = Group.objects.get_or_create(name=name)
    if created or not group.permissions.exists():
        permissions = Permission.objects.filter(
            content_type__app_label='news',
            codename__in=GROUP_PERMISSIONS[name],
        )
        group.permissions.set(permissions)
    return group


def set_up_role(user):
    """Puts the user in the group for their role.

    Only readers can have subscriptions, so they are emptied for
    everyone else (the 'None' value from the task).
    """
    group = get_group(user.role.capitalize())
    user.groups.set([group])

    if user.role != user.READER:
        user.subscribed_publishers.clear()
        user.subscribed_journalists.clear()


def is_reader(user):
    """True if the user is logged in and is a reader."""
    return user.is_authenticated and user.role == user.READER


def is_journalist(user):
    """True if the user is logged in and is a journalist."""
    return user.is_authenticated and user.role == user.JOURNALIST


def is_editor(user):
    """True if the user is logged in and is an editor."""
    return user.is_authenticated and user.role == user.EDITOR


def is_publisher(user):
    """True if the user is logged in and is a publisher account."""
    return user.is_authenticated and user.role == user.PUBLISHER


def visible_publishers(user):
    """The publishers this user is allowed to see.

    Readers (and visitors) see all of them so they can subscribe.
    Editors and journalists only see the ones they work for.
    A publisher account only sees its own.
    """
    # imported here so models.py and this file don't import each other
    from ..models import Publisher

    if is_editor(user):
        return user.publishers_edited.all()
    if is_journalist(user):
        return user.publishers_joined.all()
    if is_publisher(user):
        return Publisher.objects.filter(owner=user)
    return Publisher.objects.all()


def works_for(user, publisher):
    """True if the user is an editor of this publisher."""
    if publisher is None:
        return False
    return publisher.editors.filter(id=user.id).exists()


def articles_for_editor(articles, editor):
    """Only keeps the articles from publishers where they are an editor.

    Independent articles have no editor, the journalist publishes them.
    """
    return articles.filter(publisher__editors=editor).distinct()


def can_approve(user, article):
    """True if the user is an editor of the article's publisher."""
    if not user.has_perm('news.approve_article'):
        return False
    return works_for(user, article.publisher)


def can_publish(user, article):
    """True if a journalist can publish their own independent article."""
    return (
        is_journalist(user)
        and article.author == user
        and article.publisher is None
        and not article.approved
    )


def can_change(user, article_or_newsletter):
    """True if the user may edit or delete an article or newsletter.

    Journalists can only change their own. Editors can change the ones
    from publishers they work for.
    """
    model_name = article_or_newsletter._meta.model_name
    if not user.has_perm(f'news.change_{model_name}'):
        return False
    if is_editor(user):
        return works_for(user, article_or_newsletter.publisher)
    return article_or_newsletter.author == user


def can_view_article(user, article):
    """Approved articles are for everyone. Unapproved ones are only for
    the author and the editors who look after them."""
    if article.approved:
        return True
    if not user.is_authenticated:
        return False
    return article.author == user or can_approve(user, article)


def subscribed_articles(reader):
    """Approved articles from the reader's publishers and journalists."""
    # imported here so models.py and this file don't import each other
    from ..models import Article

    from_followed = (
        Q(publisher__in=reader.subscribed_publishers.all())
        | Q(author__in=reader.subscribed_journalists.all())
    )
    articles = Article.objects.filter(from_followed, approved=True)
    return articles.select_related('author', 'publisher').distinct()


def visible_newsletters(user):
    """The newsletters this user should see.

    Readers see all of them. Journalists see their own. Editors and
    publishers see the ones from their publishers.
    """
    # imported here so models.py and this file don't import each other
    from ..models import Newsletter

    newsletters = Newsletter.objects.select_related('author', 'publisher')
    if is_journalist(user):
        return newsletters.filter(author=user)
    if is_editor(user) or is_publisher(user):
        return newsletters.filter(publisher__in=visible_publishers(user))
    return newsletters
