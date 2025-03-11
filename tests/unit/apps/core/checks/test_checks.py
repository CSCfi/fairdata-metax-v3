import pytest
from datetime import timedelta
from uuid import UUID

from django.utils import timezone

from apps.core.checks import check_v2_sync
from apps.core.models.sync import SyncAction, V2SyncStatus


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
