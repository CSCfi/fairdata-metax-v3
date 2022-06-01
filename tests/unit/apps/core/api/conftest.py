import os
import json
import pytest
import logging

from django.urls import reverse
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


@pytest.fixture
def post_datacatalog_payloads_a_b_c(client, datacatalog_a_json, datacatalog_b_json, datacatalog_c_json):
    url = '/rest/v3/datacatalog'
    res1 = client.post(url, datacatalog_a_json, content_type='application/json')
    res2 = client.post(url, datacatalog_b_json, content_type='application/json')
    res3 = client.post(url, datacatalog_c_json, content_type='application/json')
    return res1, res2, res3
