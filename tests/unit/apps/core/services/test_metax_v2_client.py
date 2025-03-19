import logging
import uuid

import pytest

from apps.core import factories
from apps.core.models.legacy import LegacyDataset
from apps.core.services import MetaxV2Client

pytestmark = [pytest.mark.django_db]


def test_update_api_meta(mock_v2_integration, caplog):
    logging.disable(logging.NOTSET)
    dataset = factories.PublishedDatasetFactory(api_version=2)
    MetaxV2Client().update_api_meta(dataset)
    assert mock_v2_integration["any"].call_count == 1
    assert (
        mock_v2_integration["patch"].request_history[0].url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset.id}"
    )
    assert mock_v2_integration["patch"].request_history[0].json() == {
        "identifier": str(dataset.id),
        "api_meta": {"version": 3},
    }
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert f"Marked published dataset {dataset.id}" in caplog.records[0].getMessage()


def test_update_api_meta_failed(requests_mock, mock_v2_integration, caplog):
    mock_patch = requests_mock.patch(mock_v2_integration["patch"]._url, status_code=403)

    logging.disable(logging.NOTSET)
    dataset = factories.PublishedDatasetFactory(api_version=2)
    MetaxV2Client().update_api_meta(dataset)
    assert mock_v2_integration["any"].call_count == 1
    assert (
        mock_patch.request_history[0].url == f"https://metax-v2-test/rest/v2/datasets/{dataset.id}"
    )
    assert mock_patch.request_history[0].json() == {
        "identifier": str(dataset.id),
        "api_meta": {"version": 3},
    }
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert f"Failed to mark {dataset.id}" in caplog.records[0].getMessage()


def test_update_api_meta_unsaved():
    dataset = factories.DatasetFactory.build(state="published")
    with pytest.raises(ValueError) as exc_info:
        MetaxV2Client().update_api_meta(dataset)
    assert "Dataset is not saved" in str(exc_info.value)


def test_update_api_meta_draft():
    dataset = factories.DatasetFactory(state="draft")
    with pytest.raises(ValueError) as exc_info:
        MetaxV2Client().update_api_meta(dataset)
    assert "Dataset is not published" in str(exc_info.value)


def test_update_draft_api_meta(mock_v2_integration, caplog):
    logging.disable(logging.NOTSET)
    dataset_id = uuid.UUID(int=1)
    legacy = LegacyDataset.objects.create(
        id=dataset_id, dataset_json={"identifier": str(dataset_id), "api_meta": {"version": 2}}
    )
    dataset = factories.DatasetFactory(id=dataset_id, state="draft", is_legacy=True)
    legacy.dataset = dataset
    legacy.save()
    MetaxV2Client().update_draft_api_meta(dataset)

    assert mock_v2_integration["any"].call_count == 1
    assert (
        mock_v2_integration["patch"].request_history[0].url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset.id}"
    )
    assert mock_v2_integration["patch"].request_history[0].json() == {
        "identifier": str(dataset.id),
        "api_meta": {"version": 3},
    }
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert f"Marked draft {dataset.id}" in caplog.records[0].getMessage()


def test_update_draft_api_meta_fail(requests_mock, mock_v2_integration, caplog):
    mock_patch = requests_mock.patch(mock_v2_integration["patch"]._url, status_code=403)  #

    logging.disable(logging.NOTSET)
    dataset_id = uuid.UUID(int=1)
    legacy = LegacyDataset.objects.create(
        id=dataset_id, dataset_json={"identifier": str(dataset_id), "api_meta": {"version": 2}}
    )
    dataset = factories.DatasetFactory(id=dataset_id, state="draft", is_legacy=True)
    legacy.dataset = dataset
    legacy.save()
    MetaxV2Client().update_draft_api_meta(dataset)

    assert mock_v2_integration["any"].call_count == 1
    assert (
        mock_patch.request_history[0].url == f"https://metax-v2-test/rest/v2/datasets/{dataset.id}"
    )
    assert mock_patch.request_history[0].json() == {
        "identifier": str(dataset.id),
        "api_meta": {"version": 3},
    }
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert f"Failed to mark draft {dataset.id}" in caplog.records[0].getMessage()


def test_update_draft_api_meta_draft_of(mock_v2_integration, caplog):
    logging.disable(logging.NOTSET)
    dataset_id = uuid.UUID(int=1)
    published_dataset = factories.PublishedDatasetFactory(api_version=2)
    dataset = factories.DatasetFactory(id=dataset_id, state="draft", draft_of=published_dataset)
    MetaxV2Client().update_draft_api_meta(dataset)

    assert mock_v2_integration["any"].call_count == 1
    assert (
        mock_v2_integration["patch"].request_history[0].url
        == f"https://metax-v2-test/rest/v2/datasets/{published_dataset.id}"
    )
    assert mock_v2_integration["patch"].request_history[0].json() == {
        "identifier": str(published_dataset.id),
        "api_meta": {"version": 3},
    }
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "INFO"
    assert f"Marked published dataset {published_dataset.id}" in caplog.records[0].getMessage()


def test_update_draft_api_meta_unsaved():
    dataset = factories.DatasetFactory.build(state="draft")
    with pytest.raises(ValueError) as exc_info:
        MetaxV2Client().update_draft_api_meta(dataset)
    assert "Dataset is not saved" in str(exc_info.value)


def test_update_draft_api_meta_published():
    dataset = factories.PublishedDatasetFactory()
    with pytest.raises(ValueError) as exc_info:
        MetaxV2Client().update_draft_api_meta(dataset)
    assert "Dataset is not a draft" in str(exc_info.value)
