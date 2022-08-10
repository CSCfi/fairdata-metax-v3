import datetime
import logging
import pytest

from django.urls import reverse

from apps.core.models import DataCatalog
from apps.core.serializers.data_catalog_serializer import DataCatalogModelSerializer


logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_datastorage(client, datastorage_a_json):
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_datastorage_twice(client, datastorage_a_json):
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert "data storage with this id already exists" in str(res.data["id"])


@pytest.mark.django_db
def test_delete_datastorage(client, datastorage_a_json):
    ds_id = datastorage_a_json["id"]
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.delete(f"/rest/v3/datastorage/{ds_id}")
    assert res.status_code == 204

    res = client.get(f"/rest/v3/datastorage/{ds_id}?include_removed")
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_datastorage(client, datastorage_a_json, datastorage_a_updated_json):
    ds_id = datastorage_a_json["id"]
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.put(
        f"/rest/v3/datastorage/{ds_id}",
        datastorage_a_updated_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert "This is an updated test data storage" in str(res.data)


@pytest.mark.django_db
def test_update_invalid_datastorage(
    client, datastorage_a_json, datastorage_a_invalid_json
):
    ds_id = datastorage_a_json["id"]
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.put(
        f"/rest/v3/datastorage/{ds_id}",
        datastorage_a_invalid_json,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "This field may not be blank" in str(res.data)


@pytest.mark.django_db
def test_get_single_datastorage(client, datastorage_a_json):
    ds_id = datastorage_a_json["id"]
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.get(f"/rest/v3/datastorage/{ds_id}")
    assert res.status_code == 200


@pytest.mark.django_db
def test_get_list_datastorage(client, datastorage_a_json):
    res = client.post(
        "/rest/v3/datastorage", datastorage_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    res = client.get("/rest/v3/datastorage")
    assert res.status_code == 200


@pytest.mark.parametrize(
    "storage_filter, filter_value, filter_result",
    [
        ("id", "test-data-storage-a", 1),
        ("endpoint_url", "http://test.url.csc.fia", 1),
        ("endpoint_url", "http://test.url.csc.fi", 3),
        ("endpoint_description", "a test data storage", 2),
    ],
)
@pytest.mark.django_db
def test_filter_datastorage(
    client, post_datastorage_payloads_a_b_c, storage_filter, filter_value, filter_result
):
    res = client.get(
        "/rest/v3/datastorage?{0}={1}".format(storage_filter, filter_value)
    )
    assert res.status_code == 200
    assert len(res.data) == filter_result


@pytest.mark.django_db
def test_list_datastorages_with_simple_ordering(
    client, post_datastorage_payloads_a_b_c
):
    url = "/rest/v3/datastorage?ordering=created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data[0].get("id") == "test-data-storage-a"

    url = "/rest/v3/datastorage?ordering=-created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data[0].get("id") == "test-data-storage-c"


@pytest.mark.django_db
def test_list_datastorages_with_complex_ordering(
    client, post_datastorage_payloads_a_b_c
):
    url = "/rest/v3/datastorage?ordering=endpoint_description,created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data[1].get("id") == "test-data-storage-a"

    url = "/rest/v3/datastorage?ordering=endpoint_description,-created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data[1].get("id") == "test-data-storage-b"
