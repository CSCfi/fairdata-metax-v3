from django.middleware.csrf import get_token
from rest_framework import serializers

from apps.users.models import MetaxUser


class MetaxUserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaxUser
        fields = (
            "id",
            "username",
        )


class UserInfoSerializer(serializers.ModelSerializer):
    """Serialize user session data required by external services."""

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
        fields = ("username", "ida_projects", "metax_csrf_token")
        read_only_fields = fields
