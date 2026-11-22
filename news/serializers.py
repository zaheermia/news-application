"""Serializers for the API (they turn the models into JSON)."""
from rest_framework import serializers

from .models import CustomUser, Publisher, Article, Newsletter


class UserSerializer(serializers.ModelSerializer):
    """Shows a user without private info like the password or email."""

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'role']


class PublisherSerializer(serializers.ModelSerializer):
    """Shows a publisher with its owner, editors and journalists."""
    owner = UserSerializer(read_only=True)
    editors = UserSerializer(many=True, read_only=True)
    journalists = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Publisher
        fields = [
            'id', 'name', 'description', 'owner', 'editors', 'journalists',
        ]


def check_publisher(serializer, publisher):
    """Checks the journalist works for the publisher they picked.

    Used by the article and newsletter serializers.
    """
    if publisher is None:
        return publisher

    # when editing, check the author, otherwise whoever is logged in
    if serializer.instance is not None:
        journalist = serializer.instance.author
    else:
        journalist = serializer.context['request'].user

    if not publisher.journalists.filter(id=journalist.id).exists():
        raise serializers.ValidationError(
            "The journalist doesn't work for this publisher."
        )
    return publisher


class ArticleSerializer(serializers.ModelSerializer):
    """Shows an article. The author is whoever is logged in."""
    author = UserSerializer(read_only=True)
    publisher_name = serializers.ReadOnlyField(source='publisher.name')

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'author', 'publisher',
            'publisher_name', 'created_at', 'approved',
        ]
        # only the approve endpoint can change 'approved'
        read_only_fields = ['created_at', 'approved']

    def validate_title(self, value):
        """The title can't just be spaces."""
        if not value.strip():
            raise serializers.ValidationError("Title can't be empty.")
        return value.strip()

    def validate_publisher(self, publisher):
        """A journalist can only post for a publisher they work for.

        A published article can't move to another publisher.
        """
        article = self.instance
        if article is not None and article.approved:
            if publisher != article.publisher:
                raise serializers.ValidationError(
                    "A published article can't change its publisher."
                )
            return publisher
        return check_publisher(self, publisher)


class NewsletterSerializer(serializers.ModelSerializer):
    """Shows a newsletter and the ids of its articles."""
    author = UserSerializer(read_only=True)
    publisher_name = serializers.ReadOnlyField(source='publisher.name')
    articles = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Article.objects.filter(approved=True),
    )

    class Meta:
        model = Newsletter
        fields = [
            'id', 'title', 'description', 'created_at', 'author',
            'publisher', 'publisher_name', 'articles',
        ]
        read_only_fields = ['created_at']

    def validate_publisher(self, publisher):
        """A journalist can only use a publisher they work for."""
        return check_publisher(self, publisher)


class ApprovedArticleSerializer(serializers.Serializer):
    """Checks the data that the signal sends to /api/approved/."""
    id = serializers.IntegerField()
    title = serializers.CharField()
    author = serializers.CharField()
    publisher = serializers.CharField(allow_null=True, required=False)
