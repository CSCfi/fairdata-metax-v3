import pytest
from django.core.management import call_command

from apps.core import factories
from apps.core.models.access_rights import REMSApprovalType
from apps.core.models.catalog_record.dataset import REMSStatus

pytestmark = [
    pytest.mark.django_db,
]


def test_sync_rems_datasets(mock_rems, settings):
    dataset = factories.REMSDatasetFactory()
    dataset2 = factories.REMSDatasetFactory(
        access_rights__rems_approval_type=REMSApprovalType.MANUAL
    )
    assert dataset.rems_status == REMSStatus.NOT_PUBLISHED
    assert dataset2.rems_status == REMSStatus.NOT_PUBLISHED

    call_command("sync_rems_datasets")
    assert dataset.rems_status == REMSStatus.PUBLISHED
    assert dataset2.rems_status == REMSStatus.PUBLISHED
