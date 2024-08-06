import logging

import pytest
from django.conf import settings as django_settings
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from http.cookies import SimpleCookie

logger = logging.getLogger(__name__)


@pytest.fixture
def sso_authenticated_client(client, enable_sso, sso_session_teppo, get_sso_token):
    token = get_sso_token(sso_session_teppo)
    client.cookies = SimpleCookie({django_settings.SSO_SESSION_COOKIE: token})
    return client


@pytest.mark.django_db
def test_bearer_token_flow(sso_authenticated_client):
    # create new token
    resp = sso_authenticated_client.post(reverse("tokens"))
    assert resp.status_code == 200
    token = resp.data["token"]
    prefix = resp.data["prefix"]

    # create new client using bearer token, verify we are authenticated
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    resp = client.get(reverse("user"))
    assert resp.status_code == 200
    assert resp.data["username"] == "fd_teppo3"

    # list tokens
    resp = sso_authenticated_client.get(f"{reverse('tokens')}")
    assert resp.status_code == 200
    assert resp.data[0]["prefix"] == prefix

    # delete token
    resp = sso_authenticated_client.delete(f"{reverse('tokens')}?prefix={prefix}")
    assert resp.status_code == 303

    # verify that token no longer works
    resp = client.get(reverse("user"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_list_tokens_unauthenticated(client):
    resp = client.get(reverse("tokens"))
    assert resp.status_code == 403
