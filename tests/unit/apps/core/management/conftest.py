import json
import os
import re
import uuid
from itertools import islice

import pytest

from apps.files import factories as file_factories
from apps.files.models import File
from apps.core import factories
from apps.core.models import Dataset, MetadataProvider
from apps.core.models.catalog_record.related import FileSet
from apps.files.models import FileStorage
from apps.users.models import MetaxUser


@pytest.fixture
def test_user():
    """Create a test user."""
    user = MetaxUser.objects.create_user(username="testuser", email="test@example.com")
    user.save()
    return user


@pytest.fixture
def metadata_provider(test_user):
    """Create a metadata provider."""
    metadata_provider = factories.MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    metadata_provider.save()
    return metadata_provider


@pytest.fixture
def metadata_provider_old_admin(test_user):
    """Create a metadata provider with old admin organization for populate_admin_orgs tests."""
    metadata_provider = factories.MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="old-admin-org"
    )
    metadata_provider.save()
    return metadata_provider


@pytest.fixture
def ida_storage():
    """Create IDA file storage."""
    file_storage = file_factories.FileStorageFactory(storage_service="ida", csc_project="2001479")
    file_storage.save()
    return file_storage


@pytest.fixture
def dataset(metadata_provider, ida_storage, data_catalog):
    """Create a dataset with IDA storage."""
    # Create dataset manually to ensure metadata_owner is used correctly
    from apps.core.models import Dataset

    dataset = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    # Create file_set with the dataset
    file_set = factories.FileSetFactory(dataset=dataset, storage=ida_storage)
    # Create related DatasetMetrics record
    factories.DatasetMetricsFactory(dataset=dataset)
    return dataset


@pytest.fixture
def non_ida_storage():
    """Create non-IDA file storage."""
    file_storage = file_factories.FileStorageFactory(storage_service="pas", csc_project="2001479")
    file_storage.save()
    return file_storage


@pytest.fixture
def non_ida_dataset(metadata_provider, non_ida_storage):
    """Create a non-IDA dataset."""
    # Create dataset manually to ensure metadata_owner is used correctly
    from apps.core.models import Dataset

    dataset = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider,
        title={"en": "Non-IDA Dataset"},
    )
    # Create related DatasetMetrics record
    factories.DatasetMetricsFactory(dataset=dataset)
    return dataset


def get_mock_data(filename="legacy_metax_response.json"):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath) as json_file:
        return json.load(json_file)


@pytest.fixture
def legacy_files():
    storage = factories.FileStorageFactory(storage_service="ida", csc_project="2001479")
    file_data = get_mock_data(filename="legacy_single_response_files.json")
    for file in file_data:
        File.create_from_legacy(file, storage=storage)


@pytest.fixture
def mock_response(requests_mock):
    requests_mock.get(url="https://metax-v2-test/rest/v2/datasets", json=get_mock_data())
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets?removed=true",
        json={"results": []},
        complete_qs=False,
    )
    requests_mock.get(
        url=re.compile(r"https://metax-v2-test/rest/v2/datasets/.*/files"),
        json=[],
    )


@pytest.fixture
def mock_response_single(requests_mock):
    return {
        "dataset": requests_mock.get(
            url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
            json=get_mock_data("legacy_single_response.json"),
        ),
        "files": requests_mock.get(
            url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
            json=get_mock_data("legacy_single_response_files.json"),
        ),
        "file_ids": requests_mock.get(
            url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
            json=get_mock_data("legacy_single_response_file_ids.json"),
        ),
    }


@pytest.fixture
def mock_response_single_invalid(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["research_dataset"]["creator"] = "porkkana"
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        json=get_mock_data("legacy_single_response_files.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
        json=get_mock_data("legacy_single_response_file_ids.json"),
    )


@pytest.fixture
def mock_response_single_notfound(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["research_dataset"]["creator"] = "porkkana"
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        status_code=404,
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        status_code=404,
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
        status_code=404,
    )


@pytest.fixture
def mock_response_api_version_3(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["api_meta"]["version"] = 3
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        json=get_mock_data("legacy_single_response_files.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
        json=get_mock_data("legacy_single_response_file_ids.json"),
    )


@pytest.fixture
def mock_response_draft(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["state"] = "draft"
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        json=get_mock_data("legacy_single_response_files.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
        json=get_mock_data("legacy_single_response_file_ids.json"),
    )


@pytest.fixture
def mock_response_single_catalog(requests_mock):
    requests_mock.get(
        url="https://metax-v2-test/rest/datacatalogs/urn:nbn:fi:att:data-catalog-ida",
        json=get_mock_data("legacy_single_catalog_response.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets?data_catalog=urn:nbn:fi:att:data-catalog-ida&removed=false",
        json={
            "count": 1,
            "next": None,
            "results": [get_mock_data("legacy_single_response.json")],
        },
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets?data_catalog=urn:nbn:fi:att:data-catalog-ida&removed=true",
        json={
            "count": 0,
            "next": None,
            "results": [],
        },
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        json=get_mock_data("legacy_single_response_files.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files?id_list=true",
        json=get_mock_data("legacy_single_response_file_ids.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/datacatalogs/unknown_catalog",
        status_code=404,
    )


@pytest.fixture
def mock_response_dataset_files(requests_mock):
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=get_mock_data("legacy_single_response.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1/files",
        json=get_mock_data("legacy_single_response_files.json"),
    )
