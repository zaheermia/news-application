"""Helper functions that share an approved article.

They are called by the signal in signals.py.
"""
import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from rest_framework.authtoken.models import Token


def get_subscribers(article):
    """Gets the readers who follow the article's journalist or publisher."""
    # imported here so models.py and this file don't import each other
    from ..models import CustomUser

    follows = Q(subscribed_journalists=article.author)
    if article.publisher is not None:
        follows = follows | Q(subscribed_publishers=article.publisher)

    return CustomUser.objects.filter(
        follows,
        role=CustomUser.READER,
    ).exclude(email='').distinct()


def email_subscribers(article):
    """Emails the approved article to its subscribers.

    Returns how many people it was sent to.
    """
    emails = [user.email for user in get_subscribers(article)]
    if not emails:
        return 0

    source = article.publisher.name if article.publisher else 'Independent'
    body = (
        f"{article.title}\n"
        f"By {article.author.username} ({source})\n\n"
        f"{article.content}"
    )
    # bcc so the readers can't see each other's emails
    message = EmailMessage(
        subject=f"New article: {article.title}",
        body=body,
        bcc=emails,
    )
    try:
        message.send()
    except Exception as error:
        # the approval still counts even if the email fails
        print(f"Could not email subscribers: {error}")
        return 0
    return len(emails)


def post_to_approved_api(article, approved_by):
    """Sends the approved article to our own /api/approved/ endpoint.

    The token of the editor who approved it (or the journalist who
    published it) is used, so the endpoint knows who it was.
    Returns True if it worked.
    """
    if approved_by is None:
        print("Nobody approved it, so the article was not sent to the API.")
        return False

    token, created = Token.objects.get_or_create(user=approved_by)
    data = {
        'id': article.id,
        'title': article.title,
        'author': article.author.username,
        'publisher': article.publisher.name if article.publisher else None,
    }
    try:
        response = requests.post(
            settings.APPROVED_API_URL,
            json=data,
            headers={'Authorization': f'Token {token.key}'},
            timeout=5,
        )
    except requests.RequestException as error:
        print(f"Could not reach /api/approved/: {error}")
        return False

    if response.status_code != 201:
        print(f"/api/approved/ sent back {response.status_code}")
        return False
    return True
