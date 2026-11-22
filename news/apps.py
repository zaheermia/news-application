"""App settings for the News app."""
from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Loads the signals when the app starts."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'

    def ready(self):
        """Imports signals.py so the signals get connected."""
        from . import signals  # noqa: F401
