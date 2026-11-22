"""URL patterns for the News app."""
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views, api_views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # articles
    path(
        'articles/<int:article_id>/',
        views.article_detail,
        name='article_detail',
    ),
    path('articles/add/', views.add_article, name='add_article'),
    path(
        'articles/<int:article_id>/edit/',
        views.edit_article,
        name='edit_article',
    ),
    path(
        'articles/<int:article_id>/delete/',
        views.delete_article,
        name='delete_article',
    ),
    path(
        'articles/<int:article_id>/publish/',
        views.publish_article,
        name='publish_article',
    ),
    path('my-articles/', views.my_articles, name='my_articles'),

    # editor review
    path('review/', views.review_articles, name='review_articles'),
    path(
        'review/<int:article_id>/approve/',
        views.approve_article,
        name='approve_article',
    ),

    # publishers, journalists and subscriptions
    path('publishers/', views.publisher_list, name='publisher_list'),
    path(
        'publishers/<int:publisher_id>/',
        views.publisher_detail,
        name='publisher_detail',
    ),
    path(
        'publishers/<int:publisher_id>/subscribe/',
        views.toggle_publisher,
        name='toggle_publisher',
    ),
    path(
        'journalists/<int:user_id>/',
        views.journalist_detail,
        name='journalist_detail',
    ),
    path(
        'journalists/<int:user_id>/subscribe/',
        views.toggle_journalist,
        name='toggle_journalist',
    ),
    path('my-feed/', views.my_feed, name='my_feed'),

    # publisher accounts
    path('my-publication/', views.my_publication, name='my_publication'),
    path(
        'my-publication/remove/<int:user_id>/',
        views.remove_staff,
        name='remove_staff',
    ),

    # newsletters
    path('newsletters/', views.newsletter_list, name='newsletter_list'),
    path('newsletters/add/', views.add_newsletter, name='add_newsletter'),
    path('my-newsletters/', views.my_newsletters, name='my_newsletters'),
    path(
        'newsletters/<int:newsletter_id>/',
        views.newsletter_detail,
        name='newsletter_detail',
    ),
    path(
        'newsletters/<int:newsletter_id>/edit/',
        views.edit_newsletter,
        name='edit_newsletter',
    ),
    path(
        'newsletters/<int:newsletter_id>/delete/',
        views.delete_newsletter,
        name='delete_newsletter',
    ),

    # API
    path('api/token/', obtain_auth_token, name='api_token'),
    path('api/articles/', api_views.articles, name='api_articles'),
    path(
        'api/articles/subscribed/',
        api_views.subscribed,
        name='api_subscribed',
    ),
    path(
        'api/articles/<int:article_id>/',
        api_views.article_detail,
        name='api_article_detail',
    ),
    path(
        'api/articles/<int:article_id>/approve/',
        api_views.approve,
        name='api_approve',
    ),
    path(
        'api/articles/<int:article_id>/publish/',
        api_views.publish,
        name='api_publish',
    ),
    path('api/approved/', api_views.approved_log, name='api_approved'),
    path('api/newsletters/', api_views.newsletters, name='api_newsletters'),
    path(
        'api/newsletters/<int:newsletter_id>/',
        api_views.newsletter_detail,
        name='api_newsletter_detail',
    ),
    path('api/publishers/', api_views.publishers, name='api_publishers'),
]
