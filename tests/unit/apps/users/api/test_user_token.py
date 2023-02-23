import logging

import pytest
from rest_framework.test import force_authenticate

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_get_simple_auth_token(client, user, user_as_json):
    token_request = client.post("/auth/simple/", user_as_json)
    force_authenticate(token_request, user=user)
    assert user.has_usable_password() is True
    assert token_request.status_code == 200


@pytest.mark.django_db
def test_get_jwt_auth_token(client, user, user_as_json):
    token_request = client.post("/auth/jwt/token/", user_as_json, format="json", follow=True)
    force_authenticate(token_request, user=user)
    assert user.has_usable_password() is True
    assert token_request.status_code == 200

    payload = {"refresh": token_request.json()["refresh"]}
    refresh_request = client.post("/auth/jwt/refresh/", payload, format="json", follow=True)

    assert refresh_request.status_code == 200
