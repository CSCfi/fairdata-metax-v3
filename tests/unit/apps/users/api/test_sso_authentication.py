import logging

import jwt
import pytest
from django.conf import settings as django_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from rest_framework.test import force_authenticate

logger = logging.getLogger(__name__)
from http.cookies import SimpleCookie


@pytest.mark.django_db
def test_sso_login(client, user, enable_sso):
    resp = client.get(reverse("login") + "?next=/somewhere")
    assert resp.status_code == 302  # redirect
    assert (
        resp.url == "https://fake-sso/login"
        "?service=METAX&redirect_url=http%3A%2F%2Ftestserver%2Fsomewhere&language=en"
    )


@pytest.mark.django_db
def test_sso_login_invalid_next(client, user, enable_sso):
    resp = client.get(reverse("login") + "?next=https://www.example.com")
    assert resp.status_code == 302  # redirect
    assert (
        resp.url == "https://fake-sso/login"
        "?service=METAX&redirect_url=http%3A%2F%2Ftestserver%2F&language=en"
    )


@pytest.mark.django_db
def test_sso_login_disabled(client, disable_sso):
    resp = client.get(reverse("login"))
    assert resp.status_code == 405
    assert 'Method "GET" not allowed' in resp.data["detail"]


@pytest.mark.django_db
def test_sso_misconfiguration(client, enable_sso, settings):
    settings.SSO_SESSION_COOKIE = None
    resp = client.get("/auth/user")
    assert resp.status_code == 403
    assert "invalid_sso_configuration" in resp.data["code"]


@pytest.mark.django_db
def test_sso_logout(client, user, enable_sso, sso_session_teppo, get_sso_token):
    token = get_sso_token(sso_session_teppo)
    client.cookies = SimpleCookie({django_settings.SSO_SESSION_COOKIE: token})
    resp = client.post(reverse("logout") + "?next=/somewhere")
    assert resp.status_code == 302  # redirect
    assert (
        resp.url == "https://fake-sso/logout"
        "?service=METAX&redirect_url=http%3A%2F%2Ftestserver%2F&language=en"
    )


@pytest.mark.django_db
def test_sso_logout_sso_disabled(client, user, disable_sso):
    resp = client.post(reverse("logout"))
    assert resp.status_code == 302  # redirect
    assert resp.url == "/"


@pytest.mark.django_db
def test_sso_user(client, user, enable_sso, sso_session_teppo, get_sso_token):
    token = get_sso_token(sso_session_teppo)
    client.cookies = SimpleCookie({django_settings.SSO_SESSION_COOKIE: token})
    resp = client.get(reverse("user"))
    assert resp.status_code == 200
    assert resp.data["username"] == sso_session_teppo["fairdata_user"]["id"]
    assert resp.data["csc_projects"] == ["fd_teppo3_project"]


@pytest.mark.django_db
def test_sso_user_error(client, user, enable_sso, sso_session_teppo, get_sso_token):
    sso_session_teppo["fairdata_user"]["id"] = None
    token = get_sso_token(sso_session_teppo)
    client.cookies = SimpleCookie({django_settings.SSO_SESSION_COOKIE: token})
    resp = client.get(reverse("user"))
    assert resp.status_code == 403
    assert resp.data["code"] == "missing_fairdata_user_id"


@pytest.mark.django_db
def test_sso_user_not_logged_in(client, user, enable_sso):
    resp = client.get(reverse("user"))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Authentication credentials were not provided."


def user_status_json(user, **kwargs):
    return {
        "id": str(user.id),
        "email": "test@example.com",
        "locked": False,
        "modified": "2023-12-14T05:57:11Z",
        "name": "Test User",
        "qvain_admin_organizations": [],
        "projects": [],
        **kwargs,
    }


def test_sso_sync(enable_sso, user_client, user, requests_mock):
    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_json(user, projects=["user_project", "another_project"]),
    )

    user.fairdata_username = user.username  # make user a fairdata user

    # Recent sync, should not sync user on next request
    user.synced = timezone.now()
    user.save()

    res = user_client.get(reverse("user"))
    assert res.status_code == 200
    assert res.data["csc_projects"] == []

    # No previous sync, should sync user
    user.refresh_from_db()
    user.synced = None
    user.save()

    res = user_client.get(reverse("user"))
    assert res.status_code == 200
    assert res.data["csc_projects"] == ["user_project", "another_project"]

    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_json(user, projects=["not_yet_synced_project"]),
    )

    # Long time since sync, should sync user
    user.refresh_from_db()
    user.synced = timezone.now() - timezone.timedelta(days=28)
    user.save()
    res = user_client.get(reverse("user"))
    assert res.status_code == 200
    assert res.data["csc_projects"] == ["not_yet_synced_project"]


def test_sso_sync_locked_account(enable_sso, user_client, user, requests_mock):
    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_json(user, locked=True),
    )
    user.fairdata_username = user.username  # make user a fairdata user
    user.save()

    # User should be locked on sync
    res = user_client.get(reverse("user"))
    assert res.status_code == 403
    assert res.json()["detail"] == "User account has been deactivated."

    # User should be unlocked on sync
    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_json(user, locked=False),
    )
    res = user_client.get(reverse("user"))
    assert res.status_code == 200


def test_sso_sync_disabled(disable_sso, user_client, user, requests_mock):
    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json=user_status_json(user, projects=["notsyncing"]),
    )
    user.fairdata_username = user.username  # make user a fairdata user
    user.save()

    # Should not sync when sso is disabled
    res = user_client.get(reverse("user"))
    assert res.status_code == 200
    assert res.data["csc_projects"] == []
