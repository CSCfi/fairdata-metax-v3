import json
import os

import pytest

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/"


def load_test_json(filename):
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def v1_v3_dataset_v3_json():
    return load_test_json("v1-v3-dataset-v3.json")


@pytest.fixture
def v1_v3_data_catalog_v3_json():
    return load_test_json("v1-v3-data-catalog-v3.json")


@pytest.fixture
def post_file_payload_json():
    return load_test_json("post_file_payload.json")


@pytest.fixture
def minimal_dataset_with_files_json():
    return load_test_json("minimal_dataset_with_files.json")


@pytest.fixture
def harvested_datacatalog(admin_client, reference_data):
    datacatalog_json = load_test_json("data-catalog-harvested.json")
    res1 = admin_client.post(
        "/v3/data-catalogs", datacatalog_json, content_type="application/json"
    )
    return datacatalog_json
