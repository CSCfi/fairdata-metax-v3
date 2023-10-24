import json
import logging
import os
from typing import Dict

import pytest
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from .json_models import DatasetActor, Organization, Person

logger = logging.getLogger(__name__)

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"


def load_test_json(filename) -> Dict:
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


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


@pytest.fixture(scope="module")
def data_catalog_list_url():
    return reverse("datacatalog-list")


@pytest.fixture
def post_datacatalog_payloads_a_b_c(
    admin_client,
    datacatalog_a_json,
    datacatalog_b_json,
    datacatalog_c_json,
    reference_data,
    data_catalog_list_url,
):
    logger.info(__name__)
    url = data_catalog_list_url
    res1 = admin_client.post(url, datacatalog_a_json, content_type="application/json")
    res2 = admin_client.post(url, datacatalog_b_json, content_type="application/json")
    res3 = admin_client.post(url, datacatalog_c_json, content_type="application/json")
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
    admin_client, publisher_a_json, publisher_b_json, publisher_c_json, publisher_d_json
):
    logger.info(__name__)
    url = "/v3/publishers"
    res1 = admin_client.post(url, publisher_a_json, content_type="application/json")
    res2 = admin_client.post(url, publisher_b_json, content_type="application/json")
    res3 = admin_client.post(url, publisher_c_json, content_type="application/json")
    res4 = admin_client.post(url, publisher_d_json, content_type="application/json")
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
def metadata_provider_a_json():
    return load_test_json("metadata_provider_a.json")


@pytest.fixture
def metadata_provider_b_json():
    return load_test_json("metadata_provider_b.json")


@pytest.fixture
def metadata_provider_c_json():
    return load_test_json("metadata_provider_c.json")


@pytest.fixture
def metadata_provider_d_json():
    return load_test_json("metadata_provider_d.json")


@pytest.fixture
def metadata_provider_error_json():
    return load_test_json("metadata_provider_error.json")


@pytest.fixture
def metadata_provider_put_c_json():
    return load_test_json("metadata_provider_put_c.json")


@pytest.fixture
def post_metadata_provider_payloads_a_b_c_d(
    admin_client,
    metadata_provider_a_json,
    metadata_provider_b_json,
    metadata_provider_c_json,
    metadata_provider_d_json,
):
    logger.info(__name__)
    url = "/v3/metadata-provider"
    res1 = admin_client.post(url, metadata_provider_a_json, content_type="application/json")
    res2 = admin_client.post(url, metadata_provider_b_json, content_type="application/json")
    res3 = admin_client.post(url, metadata_provider_c_json, content_type="application/json")
    res4 = admin_client.post(url, metadata_provider_d_json, content_type="application/json")
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4
