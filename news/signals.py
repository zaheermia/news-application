"""Signals for the News app.

When an article changes from not approved to approved (an editor
approves it, or a journalist publishes an independent one), it gets
emailed to subscribers and sent to our own /api/approved/ endpoint.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Article
from .functions.notify import email_subscribers, post_to_approved_api


@receiver(pre_save, sender=Article)
def remember_old_approval(sender, instance, **kwargs):
    """Remembers if the article was already approved before this save."""
    if instance.pk is None:
        instance._was_approved = False
        return
    old = Article.objects.filter(pk=instance.pk).values('approved').first()
    instance._was_approved = bool(old and old['approved'])


@receiver(post_save, sender=Article)
def share_approved_article(sender, instance, created, **kwargs):
    """Emails and posts the article, but only the first time it's approved."""
    just_approved = instance.approved and not instance._was_approved
    if not just_approved:
        return

    # the approve / publish view puts the user on the article first
    approved_by = getattr(instance, '_approved_by', None)
    email_subscribers(instance)
    post_to_approved_api(instance, approved_by)
