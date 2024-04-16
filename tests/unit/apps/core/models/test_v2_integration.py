import re

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]

from apps.core.signals import LegacyUpdateFailed, dataset_created, dataset_updated


@pytest.mark.adapter
def test_v2_integration_create_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_created.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_v2_integration.call_count == 1
    call = mock_v2_integration.request_history[0]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_update_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_v2_integration.call_count == 2
    call = mock_v2_integration.request_history[0]
    assert call.method == "GET"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}"
    call = mock_v2_integration.request_history[1]
    assert call.method == "PUT"
    assert (
        call.url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}?migration_override"
    )


@pytest.mark.adapter
def test_v2_integration_update_dataset_notfound(
    mock_v2_integration, dataset_with_foreign_keys, v2_integration_settings, requests_mock
):
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("GET", matcher, status_code=404)
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_v2_integration.call_count == 2
    call = mock_v2_integration.request_history[0]
    assert call.method == "GET"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}"
    call = mock_v2_integration.request_history[1]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_hard_delete_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=False)
    assert mock_v2_integration.call_count == 1
    call = mock_v2_integration.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}"


@pytest.mark.xfail(reason="Soft delete not handled yet")
@pytest.mark.adapter
def test_v2_integration_soft_delete_dataset(mock_v2_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert mock_v2_integration.call_count == 1
    call = mock_v2_integration.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}"


@pytest.mark.adapter
def test_v2_integration_disabled_create_dataset(
    mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_created.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_v2_integration.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_update_dataset(
    mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_v2_integration.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_delete_dataset(
    mock_v2_integration, v2_integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_with_foreign_keys.delete(soft=False)
    assert mock_v2_integration.call_count == 0


@pytest.mark.adapter
def test_v2_integration_create_dataset_fail(
    mock_v2_integration, dataset_with_foreign_keys, requests_mock, v2_integration_settings
):
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=400)
    with pytest.raises(LegacyUpdateFailed):
        dataset_created.send(sender=None, data=dataset_with_foreign_keys)
