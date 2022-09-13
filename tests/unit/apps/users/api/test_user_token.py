import pytest
import logging
from rest_framework.test import force_authenticate

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_get_auth_token(client, user, user_as_json):

    token_request = client.post("/token/", user_as_json)
    force_authenticate(token_request, user=user)
    assert user.has_usable_password() is True
    assert token_request.status_code == 200
