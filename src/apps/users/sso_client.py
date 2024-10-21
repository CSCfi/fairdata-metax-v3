import logging
from typing import List, Tuple

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.users.models import MetaxUser

_logger = logging.getLogger(__name__)


class SSOClient:
    """Client for synchronizing user data using Fairdata SSO."""

    def __init__(self):
        self.enabled = settings.ENABLE_SSO_AUTH
        self.host = settings.SSO_HOST
        self.trusted_service_token = settings.SSO_TRUSTED_SERVICE_TOKEN
        if self.enabled and not (self.trusted_service_token and self.host):
            self.enabled = False
            _logger.warning(
                "User sync disabled due to missing SSO_TRUSTED_SERVICE_TOKEN or SSO_HOST."
            )

    def get_sso_user_status(self, username: str):
        if not self.enabled:
            return None

        payload = {
            "id": username,
            "token": self.trusted_service_token,
        }
        url = f"{self.host}/user_status"
        res = requests.post(url, payload)
        if res.status_code != 200:
            _logger.warning(f"Failed to get user data from {url}: {res.text} ")
            return None
        return res.json()

    def get_csc_project_users(self, csc_project: str) -> List[MetaxUser]:
        """Get list of CSC project members from SSO.

        Missing users are created and users memberships to csc_project are updated.
        Because the SSO request may be slow, its result is cached for a short time.
        """
        if not self.enabled:
            return []

        payload = {
            "id": csc_project,
            "token": self.trusted_service_token,
        }
        url = f"{self.host}/project_status"
        cache_key = f"csc_project_status:{csc_project}"
        users_data = cache.get(cache_key)

        if not users_data:
            res = requests.post(url, payload)
            if res.status_code != 200:
                _logger.warning(
                    f"Failed to get project status from {url}: {res.status_code} {res.text} "
                )
                return []
            users_data = res.json().get("users") or {}
            cache.set(cache_key, users_data, timeout=15 * 60)  # Cache data for a short time

        # Get or create users, update projects
        users = []
        for username, user_data in users_data.items():
            try:
                user = MetaxUser.objects.get(username=username)
            except MetaxUser.DoesNotExist:
                user = self._create_user(username, user_data)

            if csc_project not in user.csc_projects:  # Add csc_project to user projects
                user.csc_projects.append(csc_project)
                user.save()
            users.append(user)

        # Remove membership from users that are no longer project members
        removed_members = MetaxUser.objects.filter(csc_projects__contains=[csc_project]).exclude(
            id__in=[u.id for u in users]
        )
        for user in removed_members:
            user.csc_projects = [p for p in user.csc_projects if p != csc_project]
            user.save()

        return [user for user in users if user.is_active]

    def sync_user(self, user: MetaxUser) -> bool:
        """Sync user from SSO if necessary."""
        if not self.enabled:
            return False

        if not getattr(user, "fairdata_username", None):
            return False  # Non-fairdata user, no need to sync

        # No need to sync active user if synced recently
        now = timezone.now()
        if user.is_active and user.synced and (now - user.synced < timezone.timedelta(hours=8)):
            return False

        # Update user
        data = self.get_sso_user_status(user.username)
        if not data:
            return False
        user.synced = now
        user.email = data.get("email", "")
        user.is_active = not data["locked"]
        user.csc_projects = data["projects"]
        user.save()
        return True

    def _create_user(self, username: str, user_data: dict) -> MetaxUser:
        _logger.info(f"Creating new MetaxUser for username={username}")
        try:
            name = user_data["name"]
            first_name, last_name = name.split(" ", maxsplit=1)
            return MetaxUser.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                fairdata_username=username,  # TODO: Should be added to SSO response
                email=user_data.get("email", ""),
                is_active=not user_data["locked"],
                csc_projects=user_data.get("projects", []),
                synced=timezone.now(),
            )
        except Exception as e:
            _logger.error(f"Failed to create user: {e}")
            raise

    def get_or_create_user(self, username: str) -> Tuple[MetaxUser, bool]:
        try:
            return MetaxUser.objects.get(username=username), False
        except MetaxUser.DoesNotExist:
            data = self.get_sso_user_status(username)
            if not data:
                raise
            return self._create_user(username, data), True
