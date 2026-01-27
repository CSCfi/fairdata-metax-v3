import pytest
from rest_framework.exceptions import ValidationError

from apps.core import factories
from apps.rems.rems_service import REMSService
from apps.users.models import AdminOrganization

pytestmark = [pytest.mark.django_db]


def test_rems_add_organization_dac_member(mock_rems, user):
    """Test adding organization DAC member as REMS workflow handler."""
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__admin_organization=user.organization
    )
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "owner",
    ]

    user.dac_organizations = ["test_organization"]
    user.save()

    # User is now a DAC member of test_organization and should be a workflow handler
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "owner",
        "test_user",
    ]


def test_rems_remove_organization_dac_member(mock_rems, user):
    """Test removing organization DAC member from REMS workflow handlers."""
    user.dac_organizations = ["test_organization"]
    user.save()

    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__admin_organization=user.organization
    )
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "owner",
        "test_user",
    ]

    user.dac_organizations = []
    user.save()

    # User is no longer a DAC member of test_organization and is removed from handlers
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "owner",
    ]

def test_rems_disallow_manual_approval(mock_rems, user):
    """Test that manual REMS approval dataset is disallowed when organization idoes not allow it."""
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    AdminOrganization.objects.filter(id=user.organization).update(allow_manual_rems_approval=False)
    with pytest.raises(ValidationError) as ec:
        factories.REMSDatasetFactory(
            data_catalog=catalog,
            metadata_owner__admin_organization=user.organization,
            access_rights__rems_approval_type="manual",
        )

    error_msg = str(ec.value.detail['access_rights']['rems_approval_type'])
    assert "admin organization does not allow manual REMS approval" in error_msg



def test_rems_add_organization_dac_member_manual_approval(mock_rems, user):
    """Test adding organization DAC member as REMS workflow handler."""
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    AdminOrganization.objects.filter(id=user.organization).update(allow_manual_rems_approval=True)

    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        metadata_owner__admin_organization=user.organization,
        access_rights__rems_approval_type="manual",
    )

    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == ["rejecter-bot", "owner"]

    user.dac_organizations = ["test_organization"]
    user.save()

    # User is now a DAC member of test_organization and should be a workflow handler
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "rejecter-bot",
        "owner",
        "test_user",
    ]
