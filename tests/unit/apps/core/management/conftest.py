import json
import os
import re
import uuid
from itertools import islice

import pytest

from apps.files import factories
from apps.files.models import File


@pytest.fixture(autouse=True)
def v2_integration_settings(settings):
    settings.METAX_V2_HOST = "https://metax-v2-test"
    settings.METAX_V2_USER = "metax-v3-user"
    settings.METAX_V2_PASSWORD = "metax-v3-password"
    return settings


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
