import pytest
from django.urls import reverse

from apps.core import factories
from apps.core.models.sync import SyncAction, V2SyncStatus


@pytest.mark.django_db(databases=("default", "extra_connection"))
def test_admin_dataset_list_sync_to_v2(admin_client, v2_integration_settings):
    """Test DatasetAdmin.sync_to_v2 admin action."""
    dataset = factories.PublishedDatasetFactory()
    change_url = reverse("admin:core_dataset_changelist")
    data = {"action": "sync_to_v2", "_selected_action": [dataset.id]}
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200
    assert (
        V2SyncStatus.objects.using("extra_connection").get(dataset_id=dataset.id).action
        == SyncAction.UPDATE
    )


@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
def test_admin_v2_sync_status_sync_to_v2(admin_client, v2_integration_settings):
    """Test V2SyncStatusAdmin.sync_to_v2 admin action."""
    dataset = factories.PublishedDatasetFactory()

    V2SyncStatus.objects.create(id=dataset.id, dataset_id=dataset.id, action=SyncAction.CREATE)
    change_url = reverse("admin:core_v2syncstatus_changelist")
    data = {"action": "sync_to_v2", "_selected_action": [dataset.id]}
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200
    assert (
        V2SyncStatus.objects.using("extra_connection").get(dataset_id=dataset.id).action
        == SyncAction.CREATE
    )
