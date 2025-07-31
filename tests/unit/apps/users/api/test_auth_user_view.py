import pytest

from tests.utils import matchers

pytestmark = [pytest.mark.django_db]


def test_auth_user_view(user_client):
    userdata = user_client.get("/v3/auth/user").json()
    assert userdata == {
        "username": "test_user",
        "organization": "test_organization",
        "admin_organizations": ["admin.org"],
        "csc_projects": [],
        "groups": ["fairdata_users"],
        "metax_csrf_token": matchers.Any(type=str),
        "dataset_count": 0,
    }
