import datetime
import logging

import pytest

from apps.core.models import DataCatalog
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.datacatalog]


def test_create_datacatalog(client, datacatalog_a_json, reference_data, data_catalog_list_url):
    res = client.post(data_catalog_list_url, datacatalog_a_json, content_type="application/json")
    logger.info(str(res.data))
    assert res.status_code == 201


def test_create_minimal_datacatalog(
    client, datacatalog_d_json, reference_data, data_catalog_list_url
):
    res = client.post(data_catalog_list_url, datacatalog_d_json, content_type="application/json")
    logger.info(str(res.data))
    assert res.status_code == 201


def test_create_datacatalog_twice(
    client, datacatalog_a_json, reference_data, data_catalog_list_url
):
    _now = datetime.datetime.now()
    res1 = client.post(data_catalog_list_url, datacatalog_a_json, content_type="application/json")
    assert res1.status_code == 201
    res2 = client.post(data_catalog_list_url, datacatalog_a_json, content_type="application/json")
    assert res2.status_code == 400


def test_change_datacatalog(
    client, datacatalog_c_json, datacatalog_put_json, reference_data, data_catalog_list_url
):
    _now = datetime.datetime.now()

    res1 = client.post(data_catalog_list_url, datacatalog_c_json, content_type="application/json")
    response = client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-uusitesti'])}",
        datacatalog_put_json,
        content_type="application/json",
    )
    print("DATA", response.data)
    assert response.status_code == 200
    logger.info(str(response.data))
    assert len(response.data.get("language")) == 2


def test_change_datacatalog_to_minimal(
    client, datacatalog_a_json, datacatalog_d_json, reference_data, data_catalog_list_url
):
    _now = datetime.datetime.now()
    res1 = client.post(data_catalog_list_url, datacatalog_a_json, content_type="application/json")
    response = client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-testi'])}",
        datacatalog_d_json,
        content_type="application/json",
    )
    assert response.status_code == 200


def test_change_datacatalog_from_minimal(
    client, datacatalog_a_json, datacatalog_d_json, reference_data, data_catalog_list_url
):
    res1 = client.post(data_catalog_list_url, datacatalog_d_json, content_type="application/json")
    response = client.put(
        f"{reverse('datacatalog-detail', args=['urn:nbn:fi:att:data-catalog-testi'])}",
        datacatalog_a_json,
        content_type="application/json",
    )
    assert response.status_code == 200
    logger.info(f"{response.data=}")
    assert response.data.get("language")[0].get("url") == "http://lexvo.org/id/iso639-3/fin"


def test_create_datacatalog_error(
    client, datacatalog_error_json, reference_data, data_catalog_list_url
):
    res = client.post(
        data_catalog_list_url, datacatalog_error_json, content_type="application/json"
    )
    assert res.status_code == 400


def test_list_datacatalogs(client, post_datacatalog_payloads_a_b_c, data_catalog_list_url):
    response = client.get(data_catalog_list_url)
    logger.info(f"{response.data=}")
    catalog_count = DataCatalog.available_objects.all().count()
    assert response.status_code == 200
    assert response.data.get("count") == catalog_count


@pytest.mark.parametrize(
    "catalog_filter, filter_value, filter_result",
    [
        ("harvested", True, 1),
        ("dataset_schema", "att", 3),
        ("dataset_versioning_enabled", True, 1),
        ("dataset_versioning_enabled", False, 2),
        ("title__values", "katalogi", 3),
        ("title__values", "New", 1),
        ("id", "nbn:fi:att", 3),
        ("access_rights__description__values", "repo", 2),
        ("access_rights__access_type__url", "fairdata", 3),
        ("access_rights__access_type__pref_label__values", "open", 2),
        ("publisher__name", "testi", 3),
        ("publisher__homepage__url", ".fi", 3),
        ("publisher__homepage__title__values", "website", 3),
        ("language__url", "lexvo.org", 3),
        ("language__pref_label__values", "englannin kieli", 1),
        ("language__pref_label__values", "saami", 0),
    ],
)
def test_list_datacatalogs_with_filter(
    client, post_datacatalog_payloads_a_b_c, catalog_filter, filter_value, filter_result
):
    url = "/rest/v3/data-catalogs?{0}={1}".format(catalog_filter, filter_value)
    logger.info(url)
    response = client.get(url)
    logger.info(response.data)
    assert response.status_code == 200
    assert response.data.get("count") == filter_result


def test_list_datacatalogs_with_ordering(client, post_datacatalog_payloads_a_b_c):
    url = "/rest/v3/data-catalogs?ordering=created"
    response = client.get(url)
    results = response.data.get("results")
    assert response.status_code == 200
    assert results[0].get("id") == "urn:nbn:fi:att:data-catalog-testi"
    url = "/rest/v3/data-catalogs?ordering=-created"
    response = client.get(url)
    results = response.data.get("results")
    assert response.status_code == 200
    assert results[0].get("id") == "urn:nbn:fi:att:data-catalog-uusitesti"


def test_get_datacatalog_by_id(client, post_datacatalog_payloads_a_b_c):
    response = client.get("/rest/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 200
    assert response.data.get("id") == "urn:nbn:fi:att:data-catalog-uusitesti"


def test_delete_datacatalog_by_id(client, post_datacatalog_payloads_a_b_c):
    response = client.delete("/rest/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 204
    response = client.get("/rest/v3/data-catalogs/urn:nbn:fi:att:data-catalog-uusitesti")
    assert response.status_code == 404
