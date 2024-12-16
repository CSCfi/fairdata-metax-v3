import pytest
from django.core.management import call_command

from apps.users.models import MetaxUser

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


def test_create_appsupport_user():
    call_command("create_appsupport_user", "teppo", password="pass", email="teppo@example.com")
    user = MetaxUser.objects.get(username="teppo")
    assert user.email == "teppo@example.com"
    assert user.password
    assert user.is_staff
    assert not user.is_superuser
    assert list(user.groups.values_list("name", flat=True)) == ["appsupport"]
    assert user.has_perm("core.view_dataset")
