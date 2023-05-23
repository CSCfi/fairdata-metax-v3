import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_filestorage(client, filestorage_a_json, file_storage_list_url):
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_filestorage_twice(client, filestorage_a_json, file_storage_list_url):
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "file storage with this id already exists" in str(res.data["id"])


@pytest.mark.django_db
def test_delete_filestorage(client, filestorage_a_json, file_storage_list_url):
    ds_id = filestorage_a_json["id"]
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.delete(f"/v3/file-storages/{ds_id}")
    assert res.status_code == 204

    res = client.get(f"/v3/file-storages/{ds_id}?include_removed")
    assert res.status_code == 404


@pytest.mark.django_db
def test_update_filestorage(
    client, filestorage_a_json, filestorage_a_updated_json, file_storage_list_url
):
    ds_id = filestorage_a_json["id"]
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.put(
        f"/v3/file-storages/{ds_id}",
        filestorage_a_updated_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert "This is an updated test data storage" in str(res.data)


@pytest.mark.django_db
def test_update_invalid_filestorage(
    client, filestorage_a_json, filestorage_a_invalid_json, file_storage_list_url
):
    ds_id = filestorage_a_json["id"]
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.put(
        f"/v3/file-storages/{ds_id}",
        filestorage_a_invalid_json,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "This field may not be blank" in str(res.data)


@pytest.mark.django_db
def test_get_single_filestorage(client, filestorage_a_json, file_storage_list_url):
    ds_id = filestorage_a_json["id"]
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.get(f"/v3/file-storages/{ds_id}")
    assert res.status_code == 200


@pytest.mark.django_db
def test_get_list_filestorage(client, filestorage_a_json, file_storage_list_url):
    res = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    assert res.status_code == 201

    res = client.get(file_storage_list_url)
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
def test_filter_filestorage(
    client, post_filestorage_payloads_a_b_c, storage_filter, filter_value, filter_result
):
    res = client.get("/v3/file-storages?{0}={1}".format(storage_filter, filter_value))
    assert res.status_code == 200
    assert res.data.get("count") == filter_result


@pytest.mark.django_db
def test_list_filestorages_with_simple_ordering(client, post_filestorage_payloads_a_b_c):
    url = "/v3/file-storages?ordering=created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data.get("results")[0].get("id") == "test-data-storage-a"

    url = "/v3/file-storages?ordering=-created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data.get("results")[0].get("id") == "test-data-storage-c"


@pytest.mark.django_db
def test_list_filestorages_with_complex_ordering(client, post_filestorage_payloads_a_b_c):
    url = "/v3/file-storages?ordering=endpoint_description,created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data.get("results")[1].get("id") == "test-data-storage-a"

    url = "/v3/file-storages?ordering=endpoint_description,-created"
    res = client.get(url)
    assert res.status_code == 200
    assert res.data.get("results")[1].get("id") == "test-data-storage-b"
