import pytest
from django.core.management import call_command

from apps.core import factories
from apps.core.models.access_rights import REMSApprovalType
from apps.core.models.catalog_record.dataset import REMSStatus
from apps.core.models.access_rights import AccessType, AccessTypeChoices

pytestmark = [pytest.mark.django_db]


def test_sync_rems_datasets(mock_rems, settings, access_type_reference_data):
    dataset = factories.REMSDatasetFactory()
    dataset2 = factories.REMSDatasetFactory(
        access_rights__rems_approval_type=REMSApprovalType.MANUAL
    )
    assert dataset.rems_status == REMSStatus.NOT_PUBLISHED
    assert dataset2.rems_status == REMSStatus.NOT_PUBLISHED

    call_command("sync_rems_datasets")
    assert dataset.rems_status == REMSStatus.PUBLISHED
    assert dataset2.rems_status == REMSStatus.PUBLISHED

    # Removing rems_approval_type should remove dataset from REMS
    dataset.access_rights.rems_approval_type = None
    dataset.access_rights.save()

    # Changing access type to Open should remove dataset from REMS
    dataset2.access_rights.access_type = AccessType.objects.get(url=AccessTypeChoices.OPEN)
    dataset2.access_rights.save()

    assert dataset.rems_id == 1
    assert dataset2.rems_id == 2

    call_command("sync_rems_datasets")  # Disable and archive datasets in REMS

    assert dataset.rems_id is None
    assert dataset2.rems_id is None
    assert dataset.rems_status == REMSStatus.NOT_REMS
    assert dataset2.rems_status == REMSStatus.NOT_REMS
