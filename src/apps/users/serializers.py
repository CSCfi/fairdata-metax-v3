from django.middleware.csrf import get_token
from knox.models import AuthToken
from rest_framework import serializers

from django.core.cache import cache
from apps.common.serializers.fields import CommaSeparatedListField, MultiLanguageField
from apps.common.serializers.serializers import CommonModelSerializer
from apps.users.models import AdminOrganization, MetaxUser

DAY_IN_SECONDS = 86400
PAO_CACHE_TIMEOUT = DAY_IN_SECONDS


class AdminOrganizationModelSerializer(CommonModelSerializer):
    """Admin organization model serializer."""

    pref_label = MultiLanguageField(required=True)
    other_identifier = CommaSeparatedListField(required=False)
    url = serializers.URLField(required=True)

    class Meta:
        model = AdminOrganization
        fields = ("id", "pref_label", "other_identifier", "url")


class UserInfoSerializer(CommonModelSerializer):
    """User serializer with user details."""

    dataset_count = serializers.SerializerMethodField()

    # Metax internal user groups
    groups = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)

    def get_dataset_count(self, obj):
        return obj.metadataprovider_set.count()

    class Meta:
        model = MetaxUser
        fields = (
            "username",
            "csc_projects",
            "dataset_count",
            "groups",
        )
        read_only_fields = fields


class AuthenticatedUserInfoSerializer(UserInfoSerializer):
    """User serializer with user session data required by external services."""

    metax_csrf_token = serializers.SerializerMethodField()

    available_admin_organizations = serializers.SerializerMethodField()
    default_admin_organization = AdminOrganizationModelSerializer(required=False)

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

    def get_available_admin_organizations(self, obj):
        available_admin_organizations = cache.get("available_admin_organizations")
        if available_admin_organizations is None:
            available_admin_organizations = AdminOrganizationModelSerializer(
                AdminOrganization.objects.all(), many=True, context=self.context
            ).data
            cache.set(
                "available_admin_organizations",
                available_admin_organizations,
                timeout=PAO_CACHE_TIMEOUT,
            )
        return available_admin_organizations

    class Meta:
        model = MetaxUser
        cached_fields = ["available_admin_organizations"]
        fields = (
            "username",
            "organization",
            "admin_organizations",
            "default_admin_organization",
            "available_admin_organizations",
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
