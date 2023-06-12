import logging
from urllib.parse import urlencode

import jwt
from dateutil.parser import parse
from django.conf import settings
from django.middleware.csrf import rotate_token
from django.utils.translation import get_language, gettext_lazy as _
from rest_framework import authentication, exceptions

from apps.users.models import MetaxUser

logger = logging.getLogger(__name__)


class SSOAuthentication(authentication.SessionAuthentication):
    """Fairdata SSO authenticator for DRF.

    Inherits from SessionAuthentication that provides the
    enforce_csrf method used for CSRF checking."""

    def authenticate(self, request):
        """Authenticate request with data from SSO cookie.

        Creates user if user with username is not found."""
        if not self.is_sso_enabled():
            return None

        if not self.is_configuration_valid():
            raise exceptions.AuthenticationFailed(
                detail=_("SSO configuration error."), code="invalid_sso_configuration"
            )

        sso_session, token = self.get_sso_session(request)
        if not sso_session:
            return None

        user = self.get_or_create_user(sso_session)
        self.enforce_csrf(request)

        if self.sync_user_details(user, sso_session):
            # New login, rotate CSRF token
            rotate_token(request)

        if not user.is_active:
            logger.warning(f"Authentication failed: user locked {user}.")
            raise exceptions.AuthenticationFailed(
                _("User account has been deactivated."), code="fairdata_user_locked"
            )

        return (user, token)

    def is_sso_enabled(self) -> bool:
        return settings.ENABLE_SSO_AUTH

    def is_configuration_valid(self):
        missing_config_values = [
            key
            for key in [
                "SSO_HOST",
                "SSO_SECRET_KEY",
                "SSO_SESSION_COOKIE",
                "SSO_METAX_SERVICE_NAME",
            ]
            if not getattr(settings, key, None)
        ]
        if missing_config_values:
            logger.error(f"Missing SSO configuration variables: {missing_config_values}")
            return False
        return True

    def get_sso_session(self, request):
        """Parse SSO session cookie.

        Returns:
            tuple containing
            - session (dict): Parsed SSO session.
            - token (str): SSO session token.
        """
        token = request.COOKIES.get(settings.SSO_SESSION_COOKIE)
        if not token:
            return None, None

        try:
            return self.parse_sso_token(token), token
        except jwt.exceptions.DecodeError as e:
            logger.error(f"Authentication failed: {e}")
            raise exceptions.AuthenticationFailed(e)

    def parse_sso_token(self, token):
        return jwt.decode(token, key=settings.SSO_SECRET_KEY, algorithms=["HS256"])

    def get_or_create_user(self, sso_session) -> MetaxUser:
        """Get or create user object and update user details."""
        sso_user = sso_session.get("authenticated_user", {})
        fairdata_user = sso_session.get("fairdata_user", {})
        username = fairdata_user.get("id")

        if not username:
            logger.warning("Authentication failed: missing fairdata user id")
            raise exceptions.AuthenticationFailed(
                detail=_("Missing user identifier."), code="missing_fairdata_user_id"
            )

        if not sso_user.get("organization").get("id"):
            logger.warning("Authentication failed: missing organization id")
            raise exceptions.AuthenticationFailed(
                detail=_("Missing organization identifier."), code="missing_organization_id"
            )

        user: MetaxUser
        try:
            user = MetaxUser.objects.get(username=username)
        except MetaxUser.DoesNotExist:
            user = MetaxUser(username=username)
            user.set_unusable_password()  # disable password login
            user.save()

        return user

    def sync_user_details(self, user, sso_session) -> bool:
        """Update user details from SSO session.

        Updates only if SSO session is newer than latest sync.

        Returns:
            bool: True if user was updated."""
        initiated = parse(sso_session.get("initiated"))
        if (not user.synced) or (initiated > user.synced):
            sso_user = sso_session.get("authenticated_user", {})
            user.first_name = sso_user.get("firstname", "")
            user.last_name = sso_user.get("lastname", "")

            fairdata_user = sso_session.get("fairdata_user", {})
            user.is_active = not fairdata_user.get("locked", True)

            ida_projects = sso_session.get("services", {}).get("IDA", {}).get("projects", [])
            user.ida_projects = ida_projects

            user.synced = initiated
            user.save()
            return True

        return False

    def get_sso_language(self):
        """Return language to be used for SSO."""
        lang = get_language().split("-")[0]  # e.g. en-us -> en
        language_mapping = {"en": "en", "fi": "fi", "sv": "sv"}
        return language_mapping.get(lang, "en")

    def sso_login_url(self, request):
        """Get SSO login url for service"""
        nxt = request.query_params.get("next", "/")
        if not nxt.startswith("/"):
            nxt = "/"
        sso_redirect_url = request.build_absolute_uri(nxt)
        query = urlencode(
            {
                "service": settings.SSO_METAX_SERVICE_NAME,
                "redirect_url": sso_redirect_url,
                "language": self.get_sso_language(),
            }
        )
        host = settings.SSO_HOST
        login_url = f"{host}/login?{query}"
        return login_url

    def sso_logout_url(self, request):
        """Get SSO logout url for service"""
        sso_redirect_url = request.build_absolute_uri("/")
        query = urlencode(
            {
                "service": settings.SSO_METAX_SERVICE_NAME,
                "redirect_url": sso_redirect_url,
                "language": self.get_sso_language(),
            }
        )
        host = settings.SSO_HOST
        logout_url = f"{host}/logout?{query}"
        return logout_url
