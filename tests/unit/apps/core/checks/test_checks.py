from datetime import timedelta
from uuid import UUID

import pytest
from django.conf import settings
from django.utils import timezone

from apps.core import factories
from apps.core.checks import check_rems_publish, check_v2_sync
from apps.core.models.sync import SyncAction, V2SyncStatus
from apps.rems.models import REMSCatalogueItem


@pytest.mark.django_db
def test_check_v2_sync_ok():
    # Finished ok
    V2SyncStatus.objects.create(
        id=UUID(int=1),
        dataset_id=UUID(int=1),
        sync_started=timezone.now(),
        sync_stopped=timezone.now(),
        action=SyncAction.CREATE,
    )
    # Incomplete but not over stall threshold
    V2SyncStatus.objects.create(
        id=UUID(int=2),
        dataset_id=UUID(int=2),
        sync_started=timezone.now(),
        sync_stopped=None,
        action=SyncAction.UPDATE,
    )
    assert check_v2_sync() == {"sync_to_v2": {"ok": True}}


@pytest.mark.django_db
def test_check_v2_sync_fail():
    # Not marked as stopped but taking too long, maybe timed out?
    V2SyncStatus.objects.create(
        id=UUID(int=1),
        dataset_id=UUID(int=1),
        sync_started=timezone.now() - timedelta(minutes=10),
        sync_stopped=None,
        action=SyncAction.CREATE,
    )
    # Stopped with error
    V2SyncStatus.objects.create(
        id=UUID(int=2),
        dataset_id=UUID(int=2),
        sync_started=timezone.now(),
        sync_stopped=timezone.now(),
        error="something went wrong",
        action=SyncAction.UPDATE,
    )
    assert check_v2_sync() == {"sync_to_v2": {"ok": False, "fails": {"create": 1, "update": 1}}}


@pytest.mark.django_db
def test_check_rems_publish(mock_rems):
    dataset = factories.REMSDatasetFactory()
    dataset.signal_update()
    assert dataset.rems_publish_error is None
    assert REMSCatalogueItem.objects.count() == 1
    assert check_rems_publish() == {"rems_publish": {"ok": True}}


@pytest.mark.django_db
def test_check_rems_publish_fail(mock_rems, requests_mock):
    requests_mock.post(f"{settings.REMS_BASE_URL}/api/catalogue-items/create", status_code=400)
    dataset = factories.REMSDatasetFactory()
    dataset.signal_update()
    assert dataset.rems_publish_error is not None
    assert REMSCatalogueItem.objects.count() == 0
    assert check_rems_publish() == {"rems_publish": {"ok": False, "fails": 1}}
