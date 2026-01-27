import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.users.admin import MetaxUserAdmin, AdminOrganizationAdmin
from apps.users.factories import MetaxUserFactory
from apps.users.models import AdminOrganization, MetaxUser
from apps.core.factories import REMSDatasetFactory

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


class MockRequest:
    pass


def test_admin_organization_admin_readonly(mock_rems, rems_admin_organization):
    """The allow_manual_rems_approval field should be read-only if manual REMS datasets exist."""
    request = RequestFactory()
    admin = AdminOrganizationAdmin(model=AdminOrganization, admin_site=AdminSite())

    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="automatic",
    )

    assert admin.get_readonly_fields(request, rems_admin_organization) == [
        "manual_approval_rems_datasets",
    ]

    # Adding manual REMS approval dataset makes allow_manual_rems_approval read-only
    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="manual",
    )

    assert admin.get_readonly_fields(request, rems_admin_organization) == [
        "manual_approval_rems_datasets",
        "allow_manual_rems_approval",
    ]


def test_admin_organization_admin_count_manual_rems(mock_rems, rems_admin_organization):
    """AdminOrganizationAdmin should count manual REMS datasets."""
    admin = AdminOrganizationAdmin(model=AdminOrganization, admin_site=AdminSite())
    for _ in range(2):
        REMSDatasetFactory(
            metadata_owner__admin_organization=rems_admin_organization.id,
            access_rights__rems_approval_type="manual",
        )
    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="automatic",
    )

    assert admin.manual_approval_rems_datasets(rems_admin_organization) == 2
