"""Admin page set up for the News app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Publisher, Article, Newsletter


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Adds the role and subscriptions to the normal user admin page."""
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ['role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Role and subscriptions', {
            'fields': (
                'role', 'subscribed_publishers', 'subscribed_journalists',
            ),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('email', 'role')}),
    )

    def save_related(self, request, form, formsets, change):
        """Fixes the group after the admin form saves the user's groups."""
        super().save_related(request, form, formsets, change)
        form.instance.save()


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Admin page for publishers (for maintenance only)."""
    list_display = ['name', 'owner']
    filter_horizontal = ['editors', 'journalists']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin page for articles."""
    list_display = ['title', 'author', 'publisher', 'approved', 'created_at']
    list_filter = ['approved', 'publisher']


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Admin page for newsletters."""
    list_display = ['title', 'author', 'created_at']
    filter_horizontal = ['articles']
