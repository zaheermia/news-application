"""Models for the News app."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Publisher(models.Model):
    """A publication that has editors and journalists working for it.

    It is made when a user registers with the Publisher role, and that
    user (the owner) adds their own editors and journalists.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    # the publisher account that runs this publication
    owner = models.OneToOneField(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='owned_publisher',
        limit_choices_to={'role': 'publisher'},
    )
    # a publisher can have many editors and many journalists
    editors = models.ManyToManyField(
        'CustomUser',
        blank=True,
        related_name='publishers_edited',
        limit_choices_to={'role': 'editor'},
    )
    journalists = models.ManyToManyField(
        'CustomUser',
        blank=True,
        related_name='publishers_joined',
        limit_choices_to={'role': 'journalist'},
    )

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """A user with a role. The role decides which group they go in."""
    READER = 'reader'
    EDITOR = 'editor'
    JOURNALIST = 'journalist'
    PUBLISHER = 'publisher'
    ROLE_CHOICES = [
        (READER, 'Reader'),
        (EDITOR, 'Editor'),
        (JOURNALIST, 'Journalist'),
        (PUBLISHER, 'Publisher'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=READER,
    )

    # reader fields (emptied if the user is not a reader)
    subscribed_publishers = models.ManyToManyField(
        Publisher,
        blank=True,
        related_name='subscribers',
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='subscribers',
        limit_choices_to={'role': 'journalist'},
    )

    # journalist fields are the reverse relations from Article and
    # Newsletter: user.articles.all() and user.newsletters.all()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """Saves the user, then puts them in the group for their role."""
        super().save(*args, **kwargs)
        # imported here so the two files don't import each other
        from .functions.roles import set_up_role
        set_up_role(self)


class Article(models.Model):
    """A news article written by a journalist."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='articles',
        limit_choices_to={'role': 'journalist'},
    )
    # empty publisher means it's an independent article
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        # extra permission so only editors can approve publisher articles
        permissions = [
            ('approve_article', 'Can approve articles'),
        ]

    def __str__(self):
        return self.title


class Newsletter(models.Model):
    """A collection of articles put together by a journalist."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='newsletters',
    )
    # empty publisher means it's an independent newsletter
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='newsletters',
    )
    articles = models.ManyToManyField(
        Article,
        blank=True,
        related_name='newsletters',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
