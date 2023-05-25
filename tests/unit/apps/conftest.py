import pytest
from rest_framework.test import APIClient

from apps.users.models import MetaxUser


@pytest.fixture
def user():
    user, created = MetaxUser.objects.get_or_create(
        username="test_user", first_name="Teppo", last_name="Testaaja", is_hidden=False
    )
    user.set_password("teppo")
    user.save()
    return user
