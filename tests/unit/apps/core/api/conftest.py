import json
import logging
import os

import pytest
from rest_framework.test import APIClient

logger = logging.getLogger(__name__)

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"


def load_test_json(filename):
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def dataset_a_json():
    return load_test_json("dataset_a.json")


@pytest.fixture
def dataset_b_json():
    return load_test_json("dataset_b.json")


@pytest.fixture
def datacatalog_a_json():
    return load_test_json("datacatalog_a.json")


@pytest.fixture
def datacatalog_b_json():
    return load_test_json("datacatalog_b.json")


@pytest.fixture
def datacatalog_c_json():
    return load_test_json("datacatalog_c.json")


@pytest.fixture
def datacatalog_d_json():
    return load_test_json("datacatalog_d.json")


@pytest.fixture
def datacatalog_put_json():
    return load_test_json("datacatalog_put.json")


@pytest.fixture
def datacatalog_error_json():
    return load_test_json("datacatalog_error.json")


@pytest.fixture
def post_datacatalog_payloads_a_b_c(
    client,
    datacatalog_a_json,
    datacatalog_b_json,
    datacatalog_c_json,
    reference_data,
):
    logger.info(__name__)
    url = "/rest/v3/datacatalog"
    res1 = client.post(url, datacatalog_a_json, content_type="application/json")
    res2 = client.post(url, datacatalog_b_json, content_type="application/json")
    res3 = client.post(url, datacatalog_c_json, content_type="application/json")
    logger.info(f"{res1=}, {res2=}, {res3=}")
    return res1, res2, res3


@pytest.fixture
def publisher_a_json():
    return load_test_json("publisher_a.json")


@pytest.fixture
def publisher_b_json():
    return load_test_json("publisher_b.json")


@pytest.fixture
def publisher_c_json():
    return load_test_json("publisher_c.json")


@pytest.fixture
def publisher_d_json():
    return load_test_json("publisher_d.json")


@pytest.fixture
def publisher_error_json():
    return load_test_json("publisher_error.json")


@pytest.fixture
def publisher_put_c_json():
    with open(test_data_path + "publisher_put_c.json") as json_file:
        data = json.load(json_file)

    return data


@pytest.fixture
def post_publisher_payloads_a_b_c_d(
    client, publisher_a_json, publisher_b_json, publisher_c_json, publisher_d_json
):
    logger.info(__name__)
    url = "/rest/v3/publisher"
    res1 = client.post(url, publisher_a_json, content_type="application/json")
    res2 = client.post(url, publisher_b_json, content_type="application/json")
    res3 = client.post(url, publisher_c_json, content_type="application/json")
    res4 = client.post(url, publisher_d_json, content_type="application/json")
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4


@pytest.fixture
def access_right_alfa_json():
    return load_test_json("access_right_alfa.json")


@pytest.fixture
def access_right_beta_json():
    return load_test_json("access_right_beta.json")


@pytest.fixture
def access_right_gamma_json():
    return load_test_json("access_right_gamma.json")


@pytest.fixture
def access_right_delta_json():
    return load_test_json("access_right_delta.json")


@pytest.fixture
def access_right_put_alfa_json():
    return load_test_json("access_right_put_alfa.json")


@pytest.fixture
def dataset_access_right_error_json():
    return load_test_json("access_right_error.json")
