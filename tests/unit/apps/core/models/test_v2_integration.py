import re

import pytest

from apps.core.factories import DatasetActorFactory
from apps.core.models.catalog_record.dataset import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]

from apps.core.signals import dataset_created, dataset_updated


@pytest.fixture
def integration_settings(settings):
    settings.METAX_V2_INTEGRATION_ENABLED = True
    settings.METAX_V2_HOST = "https://metax-v2-test"
    settings.METAX_V2_USER = "metax-v3-user"
    settings.METAX_V2_PASSWORD = "metax-v3-password"
    return settings


@pytest.fixture
def integration_settings_disabled(integration_settings):
    integration_settings.METAX_V2_INTEGRATION_ENABLED = False
    return integration_settings


@pytest.fixture
def mock_integration(requests_mock, integration_settings):
    matcher = re.compile(integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=201)
    requests_mock.register_uri("DELETE", matcher, status_code=204)
    requests_mock.register_uri("GET", matcher, status_code=200)
    requests_mock.register_uri("PUT", matcher, status_code=200)
    yield requests_mock


@pytest.fixture
def mock_integration_notfound(requests_mock, integration_settings):
    matcher = re.compile(integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=201)
    requests_mock.register_uri("DELETE", matcher, status_code=204)
    requests_mock.register_uri("GET", matcher, status_code=404)
    requests_mock.register_uri("PUT", matcher, status_code=200)
    yield requests_mock


@pytest.mark.adapter
def test_v2_integration_create_dataset(mock_integration, dataset_with_foreign_keys):
    dataset_created.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_integration.call_count == 1
    call = mock_integration.request_history[0]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_update_dataset(mock_integration, dataset_with_foreign_keys):
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_integration.call_count == 2
    call = mock_integration.request_history[0]
    assert call.method == "GET"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}"
    call = mock_integration.request_history[1]
    assert call.method == "PUT"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}?migration_override"


@pytest.mark.adapter
def test_v2_integration_update_dataset_notfound(
    mock_integration_notfound, dataset_with_foreign_keys
):
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_integration_notfound.call_count == 2
    call = mock_integration_notfound.request_history[0]
    assert call.method == "GET"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_with_foreign_keys.id}"
    call = mock_integration_notfound.request_history[1]
    assert call.method == "POST"
    assert call.url == "https://metax-v2-test/rest/v2/datasets?migration_override"


@pytest.mark.adapter
def test_v2_integration_hard_delete_dataset(mock_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=False)
    assert mock_integration.call_count == 1
    call = mock_integration.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}"


@pytest.mark.xfail(reason="Soft delete not handled yet")
@pytest.mark.adapter
def test_v2_integration_soft_delete_dataset(mock_integration, dataset_with_foreign_keys):
    dataset_id = dataset_with_foreign_keys.id
    dataset_with_foreign_keys.delete(soft=True)
    assert mock_integration.call_count == 1
    call = mock_integration.request_history[0]
    assert call.method == "DELETE"
    assert call.url == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}"


@pytest.mark.adapter
def test_v2_integration_disabled_create_dataset(
    mock_integration, integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_created.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_integration.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_update_dataset(
    mock_integration, integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_updated.send(sender=None, data=dataset_with_foreign_keys)
    assert mock_integration.call_count == 0


@pytest.mark.adapter
def test_v2_integration_disabled_delete_dataset(
    mock_integration, integration_settings_disabled, dataset_with_foreign_keys
):
    dataset_with_foreign_keys.delete(soft=False)
    assert mock_integration.call_count == 0
