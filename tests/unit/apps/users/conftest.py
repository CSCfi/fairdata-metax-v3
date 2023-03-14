import logging

import pytest
from rest_framework.test import APIClient

from apps.users.models import MetaxUser


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_as_json():
    return {"username": "test_user", "password": "teppo"}
