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


@pytest.fixture
def post_datacatalog_payloads_a_b_c(client, datacatalog_a_json, datacatalog_b_json, datacatalog_c_json):
    logger.info(__name__)
    url = '/rest/v3/datacatalog'
    res1 = client.post(url, datacatalog_a_json, content_type='application/json')
    res2 = client.post(url, datacatalog_b_json, content_type='application/json')
    res3 = client.post(url, datacatalog_c_json, content_type='application/json')
    logger.info(f"{res1=}, {res2=}, {res3=}")
    return res1, res2, res3


@pytest.fixture
def dataset_language_fin_json():
    with open(test_data_path + "dataset_language_fin.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_language_est_json():
    with open(test_data_path + "dataset_language_est.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_language_spa_json():
    with open(test_data_path + "dataset_language_spa.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_language_swe_json():
    with open(test_data_path + "dataset_language_swe.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_language_put_fin_json():
    with open(test_data_path + "dataset_language_put_fin.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_language_error_json():
    with open(test_data_path + "dataset_language_error.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def post_dataset_languages(client, dataset_language_est_json, dataset_language_fin_json, dataset_language_spa_json, dataset_language_swe_json):
    logger.info(__name__)
    url = '/rest/v3/datasetlanguage'
    res1 = client.post(url, dataset_language_est_json, content_type='application/json')
    res2 = client.post(url, dataset_language_fin_json, content_type='application/json')
    res3 = client.post(url, dataset_language_swe_json, content_type='application/json')
    res4 = client.post(url, dataset_language_spa_json, content_type='application/json')
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4
