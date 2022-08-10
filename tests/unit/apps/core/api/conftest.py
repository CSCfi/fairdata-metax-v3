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
def post_datacatalog_payloads_a_b_c(
    client, datacatalog_a_json, datacatalog_b_json, datacatalog_c_json
):
    logger.info(__name__)
    url = "/rest/v3/datacatalog"
    res1 = client.post(url, datacatalog_a_json, content_type="application/json")
    res2 = client.post(url, datacatalog_b_json, content_type="application/json")
    res3 = client.post(url, datacatalog_c_json, content_type="application/json")
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
def post_dataset_language_payloads(
    client,
    dataset_language_est_json,
    dataset_language_fin_json,
    dataset_language_spa_json,
    dataset_language_swe_json,
):
    logger.info(__name__)
    url = "/rest/v3/datasetlanguage"
    res1 = client.post(url, dataset_language_est_json, content_type="application/json")
    res2 = client.post(url, dataset_language_fin_json, content_type="application/json")
    res3 = client.post(url, dataset_language_swe_json, content_type="application/json")
    res4 = client.post(url, dataset_language_spa_json, content_type="application/json")
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4

@pytest.fixture
def publisher_a_json():
    with open(test_data_path + "publisher_a.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def publisher_b_json():
    with open(test_data_path + "publisher_b.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def publisher_c_json():
    with open(test_data_path + "publisher_c.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def publisher_d_json():
    with open(test_data_path + "publisher_d.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def publisher_error_json():
    with open(test_data_path + "publisher_error.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def publisher_put_c_json():
    with open(test_data_path + "publisher_put_c.json") as json_file:
        data = json.load(json_file)

    return data


@pytest.fixture
def post_publisher_payloads_a_b_c_d(client, publisher_a_json, publisher_b_json, publisher_c_json, publisher_d_json):
    logger.info(__name__)
    url = '/rest/v3/publisher'
    res1 = client.post(url, publisher_a_json, content_type='application/json')
    res2 = client.post(url, publisher_b_json, content_type='application/json')
    res3 = client.post(url, publisher_c_json, content_type='application/json')
    res4 = client.post(url, publisher_d_json, content_type='application/json')
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4


@pytest.fixture
def access_right_alfa_json():
    with open(test_data_path + "access_right_alfa.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def access_right_beta_json():
    with open(test_data_path + "access_right_beta.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def access_right_gamma_json():
    with open(test_data_path + "access_right_gamma.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def access_right_delta_json():
    with open(test_data_path + "access_right_delta.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def access_right_put_alfa_json():
    with open(test_data_path + "access_right_put_alfa.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def dataset_access_right_error_json():
    with open(test_data_path + "access_right_error.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def post_access_rights_payloads(
    client,
    access_right_alfa_json,
    access_right_beta_json,
    access_right_gamma_json,
    access_right_delta_json,
):
    logger.info(__name__)
    url = "/rest/v3/accessright"
    res1 = client.post(url, access_right_alfa_json, content_type="application/json")
    res2 = client.post(url, access_right_beta_json, content_type="application/json")
    res3 = client.post(url, access_right_gamma_json, content_type="application/json")
    res4 = client.post(url, access_right_delta_json, content_type="application/json")
    logger.info(f"{res1=}, {res2=}, {res3=}, {res4=}")
    return res1, res2, res3, res4

@pytest.fixture
def datastorage_a_json():
    with open(test_data_path + "datastorage_a.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datastorage_b_json():
    with open(test_data_path + "datastorage_b.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datastorage_c_json():
    with open(test_data_path + "datastorage_c.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datastorage_a_updated_json():
    with open(test_data_path + "datastorage_a_updated.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def datastorage_a_invalid_json():
    with open(test_data_path + "datastorage_a_invalid.json") as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def post_datastorage_payloads_a_b_c(
    client, datastorage_a_json, datastorage_b_json, datastorage_c_json
):
    url = "/rest/v3/datastorage"
    res1 = client.post(url, datastorage_a_json, content_type="application/json")
    res2 = client.post(url, datastorage_b_json, content_type="application/json")
    res3 = client.post(url, datastorage_c_json, content_type="application/json")
    return res1, res2, res3
