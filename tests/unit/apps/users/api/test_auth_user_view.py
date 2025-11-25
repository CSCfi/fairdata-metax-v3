import pytest

from tests.utils import matchers

from apps.users.serializers import AdminOrganizationModelSerializer

pytestmark = [pytest.mark.django_db]


def test_auth_user_view(user_client, admin_organizations):
    userdata = user_client.get("/v3/auth/user").json()
    default_admin_organization = next(
        admin_org for admin_org in admin_organizations if admin_org.id == "test_org"
    )

    assert userdata == {
        "username": "test_user",
        "organization": "test_organization",
        "admin_organizations": ["admin.org"],
        "available_admin_organizations": AdminOrganizationModelSerializer(
            admin_organizations, many=True
        ).data,
        "csc_projects": [],
        "groups": ["fairdata_users"],
        "metax_csrf_token": matchers.Any(type=str),
        "dataset_count": 0,
    }
