"""Tests for syncing dataset files to V2 using the legacy files_from_v3 endpoint."""

import logging
import re

import pytest
from tests.unit.apps.core.api.conftest import load_test_json

from apps.core import factories
from apps.core.models.catalog_record.related import FileSet
from apps.core.models.file_metadata import FileSetFileMetadata
from apps.files.models import File
from apps.refdata.models import UseCategory

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def callback(request, context):
    context.status_code = 200
    return {}


def fail_callback(request, context):
    context.status_code = 400
    return {}


@pytest.fixture
def mock_v2_dataset_files_integration(requests_mock, v2_integration_settings):
    logging.disable(logging.NOTSET)
    host = v2_integration_settings.METAX_V2_HOST
    re_host = re.escape(host)
    files_path = re.compile(f"{re_host}/rest/v2/datasets/([^/]+)/files_from_v3")
    dataset_path = re.compile(f"{re_host}/rest/v2/datasets/([^/]+)")
    datasets_path = f"{host}/rest/v2/datasets"
    return {
        "datasets_mock": requests_mock.post(datasets_path, status_code=201),
        "dataset_mock": requests_mock.get(dataset_path, status_code=404),
        "sync_mock": requests_mock.post(files_path, json=callback),
    }


@pytest.fixture
def mock_v2_dataset_files_integration_fail(requests_mock, v2_integration_settings):
    logging.disable(logging.NOTSET)
    host = v2_integration_settings.METAX_V2_HOST
    re_host = re.escape(host)
    files_path = re.compile(f"{re_host}/rest/v2/datasets/([^/]+)/files_from_v3")
    dataset_path = re.compile(f"{re_host}/rest/v2/datasets/([^/]+)")
    datasets_path = f"{host}/rest/v2/datasets"
    return {
        "datasets_mock": requests_mock.post(datasets_path, status_code=201),
        "dataset_mock": requests_mock.get(dataset_path, status_code=404),
        "sync_mock": requests_mock.post(files_path, json=fail_callback),
    }


@pytest.fixture
def synced_files(deep_file_tree):
    files = deep_file_tree["files"].values()
    for index, file in enumerate(files, start=1):
        file.legacy_id = index
    File.objects.bulk_update(files, fields=["legacy_id"])
    return deep_file_tree


def test_dataset_files_legacy_sync(
    admin_client, synced_files, data_urls, mock_v2_dataset_files_integration
):
    files = synced_files["files"]
    dataset = factories.PublishedDatasetFactory()
    actions = {
        **synced_files["params"],
        "directory_actions": [{"pathname": "/"}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"], {"fileset": actions}, content_type="application/json"
    )
    assert res.status_code == 200
    mock = mock_v2_dataset_files_integration["sync_mock"]

    assert mock.call_count == 1
    request_data = mock.request_history[0].json()
    assert sorted(request_data["file_ids"]) == sorted([file.legacy_id for file in files.values()])
    assert request_data["user_metadata"] == {"files": [], "directories": []}


def test_dataset_files_legacy_sync_fail(
    admin_client, synced_files, data_urls, mock_v2_dataset_files_integration_fail
):
    dataset = factories.PublishedDatasetFactory()
    actions = {
        **synced_files["params"],
        "directory_actions": [{"pathname": "/"}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"], {"fileset": actions}, content_type="application/json"
    )
    assert res.status_code == 409  # Failed due to 400 from v2
    mock = mock_v2_dataset_files_integration_fail["sync_mock"]
    assert mock.call_count == 1  # V2 files_from_v3 should be called once


def test_dataset_files_legacy_sync_missing_legacy_id(
    admin_client, deep_file_tree, data_urls, mock_v2_dataset_files_integration
):
    dataset = factories.PublishedDatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "directory_actions": [{"pathname": "/"}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"], {"fileset": actions}, content_type="application/json"
    )
    assert res.status_code == 409  # Sync fails due to missing legacy_ids
    mock = mock_v2_dataset_files_integration["sync_mock"]
    assert not mock.called  # V2 files_from_v3 should not be called


def test_dataset_files_legacy_sync_metadata(
    admin_client,
    synced_files,
    data_urls,
    mock_v2_dataset_files_integration,
    use_category_reference_data,
    file_type_reference_data,
):
    files = synced_files["files"]
    dataset = factories.PublishedDatasetFactory()
    actions = {
        **synced_files["params"],
        "file_actions": [
            {
                "pathname": "/dir2/subdir1/file1.txt",
                "dataset_metadata": {
                    "title": "File1 title",
                    "description": "File1 description",
                    "file_type": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/file_type/code/text",
                    },
                    "use_category": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                },
            }
        ],
        "directory_actions": [
            {
                "pathname": "/",
                "dataset_metadata": {
                    "title": "Root directory title",
                    "description": "Root directory description",
                    "use_category": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                },
            },
            {
                "pathname": "/dir2/",
                "dataset_metadata": {
                    "title": "Directory2 title",
                    "description": "Directory2 description",
                    "use_category": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                },
            },
        ],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"], {"fileset": actions}, content_type="application/json"
    )
    assert res.status_code == 200
    mock = mock_v2_dataset_files_integration["sync_mock"]

    assert mock.call_count == 1
    request_data = mock.request_history[0].json()
    assert sorted(request_data["file_ids"]) == sorted([file.legacy_id for file in files.values()])
    request_data["user_metadata"]["directories"] = sorted(
        request_data["user_metadata"]["directories"], key=lambda d: d["directory_path"]
    )
    assert request_data["user_metadata"] == {
        "files": [
            {
                "identifier": str(files["/dir2/subdir1/file1.txt"].storage_identifier),
                "title": "File1 title",
                "description": "File1 description",
                "file_type": {
                    "identifier": "http://uri.suomi.fi/codelist/fairdata/file_type/code/text"
                },
                "use_category": {
                    "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                },
            }
        ],
        "directories": [
            {
                "directory_path": "/",
                "title": "Root directory title",
                "description": "Root directory description",
                "use_category": {
                    "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                },
            },
            {
                "directory_path": "/dir2",
                "title": "Directory2 title",
                "description": "Directory2 description",
                "use_category": {
                    "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                },
            },
        ],
    }


def test_dataset_files_legacy_ignore_draft(
    admin_client,
    data_catalog,
    mock_v2_dataset_files_integration,
):
    dataset = {
        "data_catalog": data_catalog.id,
        "title": {"en": "Test dataset"},
    }
    res = admin_client.post(
        "/v3/datasets",
        dataset,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.data["state"] == "draft"
    mock = mock_v2_dataset_files_integration["sync_mock"]
    assert not mock.called


def test_dataset_files_legacy_created_with_no_files(
    admin_client,
    data_catalog,
    mock_v2_dataset_files_integration,
    reference_data,
    deep_file_tree,
):
    dataset_json = load_test_json("dataset_a.json")
    dataset_json["fileset"] = {**deep_file_tree["params"]}  # FileSet without files
    res = admin_client.post(
        "/v3/datasets",
        dataset_json,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.data["state"] == "published"
    assert res.data["fileset"]["csc_project"] == deep_file_tree["params"]["csc_project"]
    mock = mock_v2_dataset_files_integration["sync_mock"]
    assert not mock.called


def test_file_metadata_to_legacy_omit_empty(deep_file_tree, use_category_reference_data):
    dataset = factories.PublishedDatasetFactory()
    file = deep_file_tree["files"]["/dir2/subdir1/file1.txt"]
    use_category = UseCategory.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
    )
    storage = factories.FileStorageFactory()
    fs = FileSet.objects.create(dataset=dataset, storage=storage)

    # Create metadata object with some empty values (description, file_type).
    # The empty values should not be returned by to_legacy.
    md = FileSetFileMetadata.objects.create(
        file_set=fs, file=file, title="Hello world", use_category=use_category
    )
    md.to_legacy = {"title": "Hello world", "use_category": {"identifier": use_category.url}}


def test_dataset_files_legacy_sync_dataset_version(
    admin_client,
    synced_files,
    data_urls,
    mock_v2_dataset_files_integration,
    use_category_reference_data,
    file_type_reference_data,
):
    """Check behavior of file sync to V2 for preservation copy of dataset."""
    dataset = factories.PublishedDatasetFactory(preservation=factories.PreservationFactory())
    actions = {
        **synced_files["params"],
        "directory_actions": [
            {
                "pathname": "/",
                "dataset_metadata": {
                    "title": "Root directory title",
                    "description": "Root directory description",
                    "use_category": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                },
            }
        ],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"], {"fileset": actions}, content_type="application/json"
    )
    assert res.status_code == 200
    mock = mock_v2_dataset_files_integration["sync_mock"]
    mock.reset()

    preservation_copy = factories.PublishedDatasetFactory(
        preservation=factories.PreservationFactory(), file_set=factories.FileSetFactory()
    )
    dataset.preservation.dataset_version = preservation_copy.preservation
    dataset.preservation.save()
    dataset.refresh_from_db()

    assert hasattr(preservation_copy.preservation, "dataset_origin_version")
    preservation_copy.signal_update(created=True)

    # Check that files from dataset_origin_version are used in V2
    # instead of the files of the preservation version.
    assert mock.call_count == 1
    request_data = mock.request_history[0].json()
    assert set(request_data["file_ids"]) == set(
        dataset.file_set.files.values_list("legacy_id", flat=True)
    )
    assert request_data["user_metadata"] == {
        "files": [],
        "directories": [
            {
                "directory_path": "/",
                "title": "Root directory title",
                "description": "Root directory description",
                "use_category": {
                    "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                },
            }
        ],
    }
