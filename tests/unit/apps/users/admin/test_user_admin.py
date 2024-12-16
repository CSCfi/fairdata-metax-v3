import pytest
from django.contrib.admin.sites import AdminSite

from apps.users.admin import MetaxUserAdmin
from apps.users.factories import MetaxUserFactory
from apps.users.models import MetaxUser

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


class MockRequest:
    pass


@pytest.fixture
def admin_request():
    request = MockRequest()
    request.user = MetaxUserFactory(is_superuser=True)
    return request


@pytest.fixture
def staff_request():
    request = MockRequest()
    request.user = MetaxUserFactory(is_staff=True)
    return request


@pytest.fixture
def metax_user_admin():
    return MetaxUserAdmin(model=MetaxUser, admin_site=AdminSite())


def test_user_admin_as_admin(metax_user_admin, admin_request):
    user = MetaxUserFactory()
    # Flatten fieldsets to get all fields
    fieldsets = metax_user_admin.get_fieldsets(admin_request, user)
    fields = set([field for fieldset in fieldsets for field in fieldset[1]["fields"]])
    assert "password" in fields
    assert "first_name" in fields
    assert "last_name" in fields
    assert "email" in fields


def test_user_admin_as_staff(metax_user_admin, staff_request):
    user = MetaxUserFactory()
    # Flatten fieldsets to get all fields
    fieldsets = metax_user_admin.get_fieldsets(staff_request, user)
    fields = set([field for fieldset in fieldsets for field in fieldset[1]["fields"]])
    assert "password" not in fields
    assert "first_name" not in fields
    assert "last_name" not in fields
    assert "email" not in fields
