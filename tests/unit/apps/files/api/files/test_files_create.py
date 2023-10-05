import pytest
from rest_framework.fields import DateTimeField, UUIDField
from tests.utils import assert_nested_subdict


@pytest.mark.django_db
def test_files_create(client, ida_file_json):
    res = client.post(
        "/v3/files",
        ida_file_json,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert_nested_subdict(
        {
            **ida_file_json,
            "filename": "file.pdf",
            "id": UUIDField(),
            "removed": None,
        },
        res.json(),
        check_all_keys_equal=True,
    )


@pytest.mark.django_db
def test_files_create_twice(client, ida_file_json):
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 400
    assert "pathname" in res.json()


@pytest.mark.django_db
def test_files_create_and_put(client, ida_file_json):
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    del ida_file_json["size"]
    res = client.put(f"/v3/files/{res.data['id']}", ida_file_json, content_type="application/json")
    assert res.status_code == 200
    assert res.data["size"] == 0


@pytest.mark.django_db
def test_files_create_and_patch(client, ida_file_json):
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["size"] == 1024
    patch_json = {"size": 123456}
    res = client.patch(f"/v3/files/{res.data['id']}", patch_json, content_type="application/json")
    assert res.status_code == 200
    assert res.data["size"] == 123456


@pytest.mark.django_db
def test_files_create_missing_identifier(client, ida_file_json):
    del ida_file_json["storage_identifier"]
    res = client.post(
        "/v3/files",
        ida_file_json,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.data["storage_identifier"][0] == "Field is required for storage_service 'ida'"
