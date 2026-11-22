"""API views for the News app.

Log in with a token: POST your username and password to /api/token/,
then send the header  Authorization: Token <your token>
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Article, Newsletter
from .serializers import (
    ArticleSerializer,
    NewsletterSerializer,
    PublisherSerializer,
    ApprovedArticleSerializer,
)
from .functions.roles import (
    is_reader,
    is_editor,
    is_journalist,
    visible_publishers,
    visible_newsletters,
    can_approve,
    can_publish,
    can_change,
    can_view_article,
    subscribed_articles,
)


def forbidden(message):
    """Sends back a 403 error with a message."""
    return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)


# ---------- Articles ----------

@api_view(['GET', 'POST'])
def articles(request):
    """GET shows all approved articles. POST lets a journalist add one."""
    if request.method == 'GET':
        approved = Article.objects.filter(approved=True).select_related(
            'author', 'publisher'
        )
        return Response(ArticleSerializer(approved, many=True).data)

    if not request.user.has_perm('news.add_article'):
        return forbidden('Only journalists can create articles.')

    serializer = ArticleSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        # new articles always start as not approved
        serializer.save(author=request.user, approved=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def subscribed(request):
    """Shows a reader the approved articles they subscribed to."""
    if not is_reader(request.user):
        return forbidden('Only readers have subscriptions.')
    serializer = ArticleSerializer(
        subscribed_articles(request.user),
        many=True,
    )
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
def article_detail(request, article_id):
    """GET shows one article. PUT changes it. DELETE removes it."""
    article = get_object_or_404(Article, id=article_id)

    if request.method == 'GET':
        if not can_view_article(request.user, article):
            return forbidden('This article has not been approved yet.')
        return Response(ArticleSerializer(article).data)

    if request.method == 'PUT':
        if not can_change(request.user, article):
            return forbidden('You are not allowed to change this article.')
        # partial so you only have to send the fields you want to change
        serializer = ArticleSerializer(
            article,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    if not request.user.has_perm('news.delete_article'):
        return forbidden('You are not allowed to delete articles.')
    if not can_change(request.user, article):
        return forbidden('You are not allowed to delete this article.')
    article.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def approve(request, article_id):
    """Lets an editor approve an article. The signal does the rest."""
    article = get_object_or_404(Article, id=article_id)
    if not can_approve(request.user, article):
        return forbidden(
            "Only an editor of the article's publisher can approve it."
        )
    if article.approved:
        return Response(
            {'error': 'This article is already approved.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    article.approved = True
    article._approved_by = request.user  # used by the signal
    article.save()
    return Response(ArticleSerializer(article).data)


@api_view(['POST'])
def publish(request, article_id):
    """Lets a journalist publish their own independent article.

    Independent articles have no editor, so the journalist publishes
    them. The signal does the rest, the same as approval.
    """
    article = get_object_or_404(Article, id=article_id)
    if article.approved:
        return Response(
            {'error': 'This article is already published.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not can_publish(request.user, article):
        return forbidden(
            'Only the journalist can publish their own independent article.'
        )

    article.approved = True
    article._approved_by = request.user  # used by the signal
    article.save()
    return Response(ArticleSerializer(article).data)


@api_view(['POST'])
def approved_log(request):
    """Logs an approved article. The signal posts here after approval.

    This acts like sharing the article with an outside service.
    Editors (approving) and journalists (publishing) post here.
    """
    if not (is_editor(request.user) or is_journalist(request.user)):
        return forbidden('Only editors and journalists can log articles.')

    serializer = ApprovedArticleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    article = Article.objects.filter(id=data['id'], approved=True).first()
    if article is None:
        return Response(
            {'error': 'No approved article with that id.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # the "log" is printed in the terminal
    print(
        f"[APPROVED] Article {article.id} '{article.title}' "
        f"by {data['author']} published by {request.user.username}"
    )
    return Response(
        {'message': 'Approved article logged.', 'article': data},
        status=status.HTTP_201_CREATED,
    )


# ---------- Newsletters ----------

@api_view(['GET', 'POST'])
def newsletters(request):
    """GET shows the user's newsletters. POST lets a journalist make one.

    Readers see all, journalists their own, editors their publishers'.
    """
    if request.method == 'GET':
        serializer = NewsletterSerializer(
            visible_newsletters(request.user),
            many=True,
        )
        return Response(serializer.data)

    if not request.user.has_perm('news.add_newsletter'):
        return forbidden('Only journalists can create newsletters.')

    serializer = NewsletterSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def newsletter_detail(request, newsletter_id):
    """GET shows one newsletter. PUT changes it. DELETE removes it."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if request.method == 'GET':
        return Response(NewsletterSerializer(newsletter).data)

    if request.method == 'PUT':
        if not can_change(request.user, newsletter):
            return forbidden('You are not allowed to change this newsletter.')
        serializer = NewsletterSerializer(
            newsletter,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    if not request.user.has_perm('news.delete_newsletter'):
        return forbidden('You are not allowed to delete newsletters.')
    if not can_change(request.user, newsletter):
        return forbidden('You are not allowed to delete this newsletter.')
    newsletter.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Publishers ----------

@api_view(['GET'])
def publishers(request):
    """Shows the publishers this user may see, with their staff.

    Readers see all, editors and journalists the ones they work for.
    """
    publishers_list = visible_publishers(request.user).prefetch_related(
        'editors', 'journalists'
    ).select_related('owner')
    return Response(PublisherSerializer(publishers_list, many=True).data)
