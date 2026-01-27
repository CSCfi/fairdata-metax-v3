import pytest

from apps.core.factories import REMSDatasetFactory
from apps.users.models import AdminOrganization


@pytest.mark.django_db
def test_admin_organization_count_manual_rems_approval_datasets(
    mock_rems, rems_admin_organization
):
    other_org = AdminOrganization.objects.create(id="other-org", allow_manual_rems_approval=True)

    # Manual approval
    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="manual",
    )
    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="manual",
    )

    # Manual for other org
    REMSDatasetFactory(
        metadata_owner__admin_organization=other_org.id, access_rights__rems_approval_type="manual"
    )

    # Automatic
    REMSDatasetFactory(
        metadata_owner__admin_organization=rems_admin_organization.id,
        access_rights__rems_approval_type="automatic",
    )

    assert rems_admin_organization.count_manual_rems_approval_datasets() == 2
    assert other_org.count_manual_rems_approval_datasets() == 1
