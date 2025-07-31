from django.contrib.auth.validators import UnicodeUsernameValidator
from django.middleware.csrf import get_token
from knox.models import AuthToken
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from apps.common.serializers.serializers import CommonModelSerializer
from apps.users.models import MetaxUser


class MetaxUserModelSerializer(CommonModelSerializer):
    """User model serializer for use in datasets."""

    class Meta:
        model = MetaxUser
        fields = ("username",)
        extra_kwargs = {"username": {"validators": []}}

    def create(self, validated_data):
        username = validated_data.pop("username")
        return MetaxUser.objects.get_or_create(username=username, defaults=validated_data)[0]


class UserInfoSerializer(CommonModelSerializer):
    """User serializer with user details."""

    dataset_count = serializers.SerializerMethodField()

    # Metax internal user groups
    groups = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)

    def get_dataset_count(self, obj):
        return obj.metadataprovider_set.count()

    class Meta:
        model = MetaxUser
        fields = ("username", "csc_projects", "dataset_count", "groups")
        read_only_fields = fields


class AuthenticatedUserInfoSerializer(UserInfoSerializer):
    """User serializer with user session data required by external services."""

    metax_csrf_token = serializers.SerializerMethodField()

    def get_metax_csrf_token(self, obj):
        """Return CSRF token.

        Requests using cookie-based authentication (e.g. SSO session)
        need to include this in header HTTP_X_CSRFTOKEN for requests
        that modify data, like POST, PUT and DELETE.

        The token is rotated on login, so it needs to be fetched
        again on each new login. Also, Django masks the value
        for security reasons so it looks different on each request.
        """
        return get_token(self.context["request"])

    class Meta:
        model = MetaxUser
        fields = (
            "username",
            "organization",
            "admin_organizations",
            "csc_projects",
            "groups",
            "metax_csrf_token",
            "dataset_count",
        )
        read_only_fields = fields


class TokenSerializer(CommonModelSerializer):
    """Serializer for AuthTokens in API token list."""

    # Show token key (first few characters of token) to allow identifying tokens
    prefix = serializers.CharField(source="token_key", read_only=True)

    class Meta:
        model = AuthToken
        fields = ["created", "expiry", "prefix"]
