import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.core import factories
from apps.core.models.sync import SyncAction, V2SyncStatus

pytestmark = [
    pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True),
    pytest.mark.management,
    pytest.mark.adapter,
    pytest.mark.usefixtures("data_catalog", "v2_integration_settings"),
]


@pytest.fixture
def mock_sync():
    with patch("apps.core.services.MetaxV2Client.update_dataset", MagicMock()), patch(
        "apps.core.services.MetaxV2Client.update_dataset_files", MagicMock()
    ), patch("apps.core.services.MetaxV2Client.delete_dataset", MagicMock()):
        yield


def fail(*args, **kwargs):
    raise ValueError("i fail")


@pytest.fixture
def mock_sync_fail():
    with patch("apps.core.services.MetaxV2Client.update_dataset", fail), patch(
        "apps.core.services.MetaxV2Client.update_dataset_files", fail
    ), patch("apps.core.services.MetaxV2Client.delete_dataset", fail):
        yield


def test_retry_sync_datasets(mock_sync):
    err = StringIO()
    dataset = factories.PublishedDatasetFactory()
    status = V2SyncStatus.objects.create(id=dataset.id, dataset=dataset, action=SyncAction.CREATE)
    call_command("retry_sync_datasets", stderr=err)
    status.refresh_from_db()
    assert status.status == "success"


def test_retry_sync_datasets_fail(mock_sync_fail):
    err = StringIO()
    dataset = factories.PublishedDatasetFactory()
    status = V2SyncStatus.objects.create(id=dataset.id, dataset=dataset, action=SyncAction.CREATE)
    call_command("retry_sync_datasets", stderr=err)
    status.refresh_from_db()
    assert status.status == "fail"


def test_retry_sync_datasets_force_datasets(mock_sync):
    err = StringIO()
    dataset = factories.PublishedDatasetFactory()
    call_command(
        "retry_sync_datasets",
        stderr=err,
        force=True,
        identifiers=[str(dataset.id), str(uuid.UUID(int=123))],
    )
    status = V2SyncStatus.objects.get(id=dataset.id)
    assert status.status == "success"
    assert not V2SyncStatus.objects.filter(id=uuid.UUID(int=123)).exists()
