import json
import os

import pytest


def get_mock_data(filename="legacy_metax_response.json"):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath) as json_file:
        return json.load(json_file)


@pytest.fixture
def mock_response(requests_mock):
    requests_mock.get(url="https://metax-v2-test/rest/v2/datasets", json=get_mock_data())


@pytest.fixture
def mock_response_single(requests_mock):
    return requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=get_mock_data("legacy_single_response.json"),
    )


@pytest.fixture
def mock_response_single_invalid(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["research_dataset"]["creator"] = "porkkana"
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )


@pytest.fixture
def mock_response_api_version_3(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["api_meta"]["version"] = 3
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )


@pytest.fixture
def mock_response_draft(requests_mock):
    data = get_mock_data("legacy_single_response.json")
    data["state"] = "draft"
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=data,
    )


@pytest.fixture
def mock_response_single_catalog(requests_mock):
    requests_mock.get(
        url="https://metax-v2-test/rest/datacatalogs/c955e904-e3dd-4d7e-99f1-3fed446f96d1",
        json=get_mock_data("legacy_single_catalog_response.json"),
    )
    requests_mock.get(
        url="https://metax-v2-test/rest/datacatalogs/unknown_catalog",
        status_code=404,
    )
