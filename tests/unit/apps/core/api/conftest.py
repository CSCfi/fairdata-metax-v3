import os
import json
import pytest
import logging

from rest_framework.test import APIClient

logger = logging.getLogger(__name__)

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"

@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def datacatalog_a_json():
    with open(test_data_path + "datacatalog_a.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datacatalog_b_json():
    with open(test_data_path + "datacatalog_b.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datacatalog_c_json():
    with open(test_data_path + "datacatalog_c.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datacatalog_d_json():
    with open(test_data_path + "datacatalog_d.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datacatalog_put_json():
    with open(test_data_path + "datacatalog_put.json") as json_file:
        data = json.load(json_file)

    return data


@pytest.fixture
def datacatalog_error_json():
    with open(test_data_path + "datacatalog_error.json") as json_file:
        data = json.load(json_file)
    return data
