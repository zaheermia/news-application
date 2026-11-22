"""Views for the News website."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import (
    RegisterForm,
    ArticleForm,
    NewsletterForm,
    PublisherForm,
    AddStaffForm,
)
from .models import Article, Publisher, Newsletter, CustomUser
from .functions.roles import (
    is_reader,
    is_journalist,
    is_publisher,
    visible_publishers,
    visible_newsletters,
    articles_for_editor,
    can_approve,
    can_publish,
    can_change,
    can_view_article,
    subscribed_articles,
)

NOT_ALLOWED = "You are not allowed to do that."


# ---------- Home, register, login ----------

def home(request):
    """Shows all the approved articles."""
    articles = Article.objects.filter(approved=True).select_related(
        'author', 'publisher'
    )
    return render(request, 'news/home.html', {'articles': articles})


def register_user(request):
    """Makes a new account. The role picks the user's group.

    Publishers also get their publication made here.
    """
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome {user.username}!')
        if is_publisher(user):
            return redirect('my_publication')
        return redirect('home')
    return render(request, 'news/register.html', {'form': form})


def login_user(request):
    """Logs the user in."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        return render(request, 'news/login.html', {
            'error': 'Invalid username or password.',
            'username': username,
        })
    return render(request, 'news/login.html')


def logout_user(request):
    """Logs the user out."""
    logout(request)
    return redirect('login')


# ---------- Articles ----------

def article_detail(request, article_id):
    """Shows one article."""
    article = get_object_or_404(Article, id=article_id)
    if not can_view_article(request.user, article):
        return HttpResponseForbidden(NOT_ALLOWED)

    logged_in = request.user.is_authenticated
    return render(request, 'news/article_detail.html', {
        'article': article,
        'can_change': logged_in and can_change(request.user, article),
        'can_approve': (
            logged_in
            and not article.approved
            and can_approve(request.user, article)
        ),
        'can_publish': can_publish(request.user, article),
    })


@login_required
def my_articles(request):
    """Shows the journalist's own articles, published or not."""
    if not is_journalist(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    articles = request.user.articles.select_related('publisher')
    return render(request, 'news/my_articles.html', {'articles': articles})


@login_required
def add_article(request):
    """Lets a journalist write a new article."""
    if not request.user.has_perm('news.add_article'):
        return HttpResponseForbidden(NOT_ALLOWED)

    form = ArticleForm(request.POST or None, journalist=request.user)
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        article.approved = False  # not public until approved or published
        article.save()
        if article.publisher:
            messages.success(request, 'Article sent to the editors.')
        else:
            messages.success(
                request,
                'Article saved. Click Publish when you are happy with it.',
            )
        return redirect('my_articles')
    return render(request, 'news/form.html', {
        'form': form,
        'heading': 'Write an article',
    })


@login_required
def edit_article(request, article_id):
    """Lets the author or one of its editors change an article."""
    article = get_object_or_404(Article, id=article_id)
    if not can_change(request.user, article):
        return HttpResponseForbidden(NOT_ALLOWED)

    form = ArticleForm(
        request.POST or None,
        instance=article,
        journalist=article.author,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Article saved.')
        return redirect('article_detail', article_id=article.id)
    return render(request, 'news/form.html', {
        'form': form,
        'heading': 'Edit article',
    })


@login_required
def delete_article(request, article_id):
    """Asks first, then deletes the article."""
    article = get_object_or_404(Article, id=article_id)
    if not request.user.has_perm('news.delete_article'):
        return HttpResponseForbidden(NOT_ALLOWED)
    if not can_change(request.user, article):
        return HttpResponseForbidden(NOT_ALLOWED)

    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article deleted.')
        return redirect('home')
    return render(request, 'news/confirm_delete.html', {'item': article})


@login_required
@require_POST
def publish_article(request, article_id):
    """Lets a journalist publish their own independent article.

    Independent articles have no editor, so the journalist publishes
    them. The signal then emails and posts it, the same as approval.
    """
    article = get_object_or_404(Article, id=article_id)
    if not can_publish(request.user, article):
        return HttpResponseForbidden(NOT_ALLOWED)

    article.approved = True
    article._approved_by = request.user  # used by the signal
    article.save()
    messages.success(request, f'"{article.title}" was published.')
    return redirect('my_articles')


# ---------- Editor review ----------

@login_required
def review_articles(request):
    """Shows the editor the articles from their publishers to approve."""
    if not request.user.has_perm('news.approve_article'):
        return HttpResponseForbidden(NOT_ALLOWED)
    pending = Article.objects.filter(approved=False).select_related(
        'author', 'publisher'
    )
    articles = articles_for_editor(pending, request.user)
    return render(request, 'news/review_articles.html', {
        'articles': articles,
    })


@login_required
@require_POST
def approve_article(request, article_id):
    """Approves an article. The signal then emails and posts it."""
    article = get_object_or_404(Article, id=article_id)
    if not can_approve(request.user, article):
        return HttpResponseForbidden(NOT_ALLOWED)

    if article.approved:
        messages.info(request, 'That article was already approved.')
    else:
        article.approved = True
        article._approved_by = request.user  # used by the signal
        article.save()
        messages.success(request, f'"{article.title}" was approved.')
    return redirect('review_articles')


# ---------- Publishers, journalists and subscriptions ----------

def publisher_list(request):
    """Shows the publishers this user is allowed to see.

    Journalists only see their publishers in the article form.
    """
    if is_journalist(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    if is_publisher(request.user):
        return redirect('my_publication')
    return render(request, 'news/publisher_list.html', {
        'publishers': visible_publishers(request.user),
    })


def publisher_detail(request, publisher_id):
    """Shows a publisher and its approved articles."""
    if is_journalist(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    publisher = get_object_or_404(
        visible_publishers(request.user), id=publisher_id
    )
    subscribed = (
        is_reader(request.user)
        and request.user.subscribed_publishers.filter(
            id=publisher.id
        ).exists()
    )
    return render(request, 'news/publisher_detail.html', {
        'publisher': publisher,
        'articles': publisher.articles.filter(approved=True),
        'subscribed': subscribed,
    })


def journalist_detail(request, user_id):
    """Shows a journalist and their approved articles."""
    journalist = get_object_or_404(
        CustomUser, id=user_id, role=CustomUser.JOURNALIST
    )
    subscribed = (
        is_reader(request.user)
        and request.user.subscribed_journalists.filter(
            id=journalist.id
        ).exists()
    )
    return render(request, 'news/journalist_detail.html', {
        'journalist': journalist,
        'articles': journalist.articles.filter(approved=True),
        'subscribed': subscribed,
    })


@login_required
@require_POST
def toggle_publisher(request, publisher_id):
    """Subscribes or unsubscribes a reader from a publisher."""
    if not is_reader(request.user):
        return HttpResponseForbidden('Only readers can subscribe.')
    publisher = get_object_or_404(Publisher, id=publisher_id)
    subscriptions = request.user.subscribed_publishers
    if subscriptions.filter(id=publisher.id).exists():
        subscriptions.remove(publisher)
        messages.info(request, f'Unsubscribed from {publisher.name}.')
    else:
        subscriptions.add(publisher)
        messages.success(request, f'Subscribed to {publisher.name}.')
    return redirect('publisher_detail', publisher_id=publisher.id)


@login_required
@require_POST
def toggle_journalist(request, user_id):
    """Subscribes or unsubscribes a reader from a journalist."""
    if not is_reader(request.user):
        return HttpResponseForbidden('Only readers can subscribe.')
    journalist = get_object_or_404(
        CustomUser, id=user_id, role=CustomUser.JOURNALIST
    )
    subscriptions = request.user.subscribed_journalists
    if subscriptions.filter(id=journalist.id).exists():
        subscriptions.remove(journalist)
        messages.info(request, f'Unsubscribed from {journalist.username}.')
    else:
        subscriptions.add(journalist)
        messages.success(request, f'Subscribed to {journalist.username}.')
    return redirect('journalist_detail', user_id=journalist.id)


@login_required
def my_feed(request):
    """Shows a reader the articles from what they subscribed to."""
    if not is_reader(request.user):
        return HttpResponseForbidden('Only readers have a feed.')
    articles = subscribed_articles(request.user)
    return render(request, 'news/my_feed.html', {'articles': articles})


# ---------- Publisher accounts ----------

@login_required
def my_publication(request):
    """Lets a publisher change their details and add staff."""
    if not is_publisher(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    publisher = get_object_or_404(Publisher, owner=request.user)

    details_form = PublisherForm(instance=publisher)
    staff_form = AddStaffForm()

    if request.method == 'POST':
        if 'save_details' in request.POST:
            details_form = PublisherForm(request.POST, instance=publisher)
            if details_form.is_valid():
                details_form.save()
                messages.success(request, 'Publication details saved.')
                return redirect('my_publication')
        elif 'add_staff' in request.POST:
            staff_form = AddStaffForm(request.POST)
            if staff_form.is_valid():
                add_staff_member(publisher, staff_form.staff_member)
                messages.success(
                    request,
                    f'{staff_form.staff_member.username} was added.',
                )
                return redirect('my_publication')

    return render(request, 'news/my_publication.html', {
        'publisher': publisher,
        'details_form': details_form,
        'staff_form': staff_form,
        'articles': publisher.articles.filter(approved=True),
    })


def add_staff_member(publisher, user):
    """Adds an editor or journalist to the right list of the publisher."""
    if user.role == CustomUser.EDITOR:
        publisher.editors.add(user)
    else:
        publisher.journalists.add(user)


@login_required
@require_POST
def remove_staff(request, user_id):
    """Lets a publisher remove an editor or journalist."""
    if not is_publisher(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    publisher = get_object_or_404(Publisher, owner=request.user)
    staff_member = get_object_or_404(CustomUser, id=user_id)
    publisher.editors.remove(staff_member)
    publisher.journalists.remove(staff_member)
    messages.info(request, f'{staff_member.username} was removed.')
    return redirect('my_publication')


# ---------- Newsletters ----------

def newsletter_list(request):
    """Shows the newsletters this user should see.

    Journalists use My Newsletters instead.
    """
    if is_journalist(request.user):
        return redirect('my_newsletters')
    return render(request, 'news/newsletter_list.html', {
        'newsletters': visible_newsletters(request.user),
        'heading': 'Newsletters',
    })


@login_required
def my_newsletters(request):
    """Shows a journalist their own newsletters."""
    if not is_journalist(request.user):
        return HttpResponseForbidden(NOT_ALLOWED)
    return render(request, 'news/newsletter_list.html', {
        'newsletters': visible_newsletters(request.user),
        'heading': 'My Newsletters',
    })


def newsletter_detail(request, newsletter_id):
    """Shows one newsletter and its articles."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    return render(request, 'news/newsletter_detail.html', {
        'newsletter': newsletter,
        'articles': newsletter.articles.filter(approved=True),
        'can_change': (
            request.user.is_authenticated
            and can_change(request.user, newsletter)
        ),
    })


@login_required
def add_newsletter(request):
    """Lets a journalist make a newsletter."""
    if not request.user.has_perm('news.add_newsletter'):
        return HttpResponseForbidden(NOT_ALLOWED)

    form = NewsletterForm(request.POST or None, journalist=request.user)
    if request.method == 'POST' and form.is_valid():
        newsletter = form.save(commit=False)
        newsletter.author = request.user
        newsletter.save()
        form.save_m2m()  # saves the articles list
        messages.success(request, 'Newsletter made.')
        return redirect('newsletter_detail', newsletter_id=newsletter.id)
    return render(request, 'news/form.html', {
        'form': form,
        'heading': 'Make a newsletter',
    })


@login_required
def edit_newsletter(request, newsletter_id):
    """Lets the author or one of its editors change a newsletter."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    if not can_change(request.user, newsletter):
        return HttpResponseForbidden(NOT_ALLOWED)

    form = NewsletterForm(
        request.POST or None,
        instance=newsletter,
        journalist=newsletter.author,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Newsletter saved.')
        return redirect('newsletter_detail', newsletter_id=newsletter.id)
    return render(request, 'news/form.html', {
        'form': form,
        'heading': 'Edit newsletter',
    })


@login_required
def delete_newsletter(request, newsletter_id):
    """Asks first, then deletes the newsletter."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    if not request.user.has_perm('news.delete_newsletter'):
        return HttpResponseForbidden(NOT_ALLOWED)
    if not can_change(request.user, newsletter):
        return HttpResponseForbidden(NOT_ALLOWED)

    if request.method == 'POST':
        newsletter.delete()
        messages.success(request, 'Newsletter deleted.')
        return redirect('newsletter_list')
    return render(request, 'news/confirm_delete.html', {'item': newsletter})
