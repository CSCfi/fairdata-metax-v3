import pytest
from django.core.management import call_command

from apps.core import factories
from apps.core.models.catalog_record.dataset import REMSStatus

pytestmark = [
    pytest.mark.django_db,
]


def test_sync_rems_datasets(mock_rems, settings):
    dataset = factories.REMSDatasetFactory()
    assert dataset.rems_status is REMSStatus.NOT_PUBLISHED

    call_command("sync_rems_datasets")
    assert dataset.rems_status == REMSStatus.PUBLISHED
