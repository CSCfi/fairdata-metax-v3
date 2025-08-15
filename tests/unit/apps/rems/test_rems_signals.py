import pytest

from apps.core import factories
from apps.rems.rems_service import REMSService

pytestmark = [pytest.mark.django_db]


def test_rems_add_organization_dac_member(mock_rems, user):
    """Test adding organization DAC member as REMS workflow handler."""
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__organization=user.organization
    )
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == ["approver-bot", "rejecter-bot"]

    user.dac_organizations = ["test_organization"]
    user.save()

    # User is now a DAC member of test_organization and should be a workflow handler
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "test_user",
    ]


def test_rems_remove_organization_dac_member(mock_rems, user):
    """Test removing organization DAC member from REMS workflow handlers."""
    user.dac_organizations = ["test_organization"]
    user.save()

    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__organization=user.organization
    )
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == [
        "approver-bot",
        "rejecter-bot",
        "test_user",
    ]

    user.dac_organizations = []
    user.save()

    # User is no longer a DAC member of test_organization and is removed from handlers
    assert len(mock_rems.entities["workflow"]) == 1
    assert mock_rems.entities["workflow"][1]["handlers"] == ["approver-bot", "rejecter-bot"]
