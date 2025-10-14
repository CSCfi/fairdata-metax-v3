import logging
import re

import pytest

pytestmark = [
    pytest.mark.django_db(databases=("default", "extra_connection")),
    pytest.mark.dataset,
]

from tests.utils import matchers

from apps.core.models.sync import SyncAction, V2SyncStatus
from apps.core.services.metax_v2_client import LegacyUpdateFailed
from apps.core.signals import dataset_created, dataset_updated


@pytest.mark.adapter
def test_v2_integration_create_dataset(
    requests_mock, mock_v2_integration, dataset_with_foreign_keys
):
    dataset_created.send(sender=None, instance=dataset_with_foreign_keys)
    assert requests_mock.call_count == 1
    call = requests_mock.request_history[0]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_update_dataset(
    requests_mock, mock_v2_integration, dataset_with_foreign_keys
):
    dataset_updated.send(sender=None, instance=dataset_with_foreign_keys)
    assert requests_mock.call_count == 2
    call = requests_mock.request_history[0]
    assert call.method == "GET"
    assert (
        call.url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}?removed"
    )
    call = requests_mock.request_history[1]
    assert call.method == "PUT"
    assert (
        call.url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}?migration_override&removed"
    )


@pytest.mark.adapter
def test_v2_integration_update_dataset_notfound(
    mock_v2_integration, dataset_with_foreign_keys, v2_integration_settings, requests_mock
):
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("GET", matcher, status_code=404)
    dataset_updated.send(sender=None, instance=dataset_with_foreign_keys)
    assert requests_mock.call_count == 2
    call = requests_mock.request_history[0]
    assert call.method == "GET"
    assert (
        call.url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}?removed"
    )
    call = requests_mock.request_history[1]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_hard_delete_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=False)
    assert mock_v2_integration["delete"].call_count == 1
    call = mock_v2_integration["delete"].request_history[0]
    assert call.method == "DELETE"
    assert (
        call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true&hard=true"
    )
    assert (
        V2SyncStatus.objects.using("extra_connection").get(id=dataset_id).action
        == SyncAction.FLUSH
    )


@pytest.mark.adapter
def test_v2_integration_soft_delete_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert mock_v2_integration["delete"].call_count == 1
    call = mock_v2_integration["delete"].request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true"
    assert (
        V2SyncStatus.objects.using("extra_connection").get(id=dataset_id).action
        == SyncAction.DELETE
    )


@pytest.mark.adapter
def test_v2_integration_hard_delete_a_soft_deleted_dataset(
    mock_v2_integration, dataset_with_foreign_keys
):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert mock_v2_integration["delete"].call_count == 1
    call = mock_v2_integration["delete"].request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true"

    dataset_with_foreign_keys.delete(soft=False)
    assert mock_v2_integration["delete"].call_count == 2
    call = mock_v2_integration["delete"].request_history[1]
    assert call.method == "DELETE"
    assert (
        call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true&hard=true"
    )


def test_v2_integration_delete_dataset_not_found_log_error(
    caplog, requests_mock, mock_v2_integration, dataset_with_foreign_keys
):
    logging.disable(logging.NOTSET)
    delete_mock = requests_mock.delete(mock_v2_integration["delete"]._url, status_code=404)

    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert delete_mock.call_count == 1
    call = delete_mock.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true"
    assert caplog.messages == [
        matchers.StringContaining(f"Dataset {dataset_id} not found from Metax v2")
    ]


@pytest.mark.adapter
def test_v2_integration_delete_dataset_log_error(
    caplog, requests_mock, mock_v2_integration, dataset_with_foreign_keys
):
    logging.disable(logging.NOTSET)
    delete_mock = requests_mock.delete(mock_v2_integration["delete"]._url, status_code=500)

    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert delete_mock.call_count == 1
    call = delete_mock.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}?removed=true"
    assert caplog.messages == [
        matchers.StringContaining(f"Sync delete {dataset_id} to V2 failed:")
    ]


@pytest.mark.adapter
def test_v2_integration_disabled_create_dataset(
    requests_mock, mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_created.send(sender=None, instance=dataset_with_foreign_keys)
    assert requests_mock.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_update_dataset(
    requests_mock, mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_updated.send(sender=None, instance=dataset_with_foreign_keys)
    assert requests_mock.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_delete_dataset(
    requests_mock, mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_with_foreign_keys.delete(soft=False)
    assert requests_mock.call_count == 0


@pytest.mark.adapter
def test_v2_integration_create_dataset_fail(
    mock_v2_integration, dataset_with_foreign_keys, requests_mock, v2_integration_settings
):
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=400)
    dataset_created.send(sender=None, instance=dataset_with_foreign_keys)
    status = dataset_with_foreign_keys.sync_status
    assert status.error is not None
