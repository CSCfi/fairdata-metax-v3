import pytest
from rest_framework.fields import UUIDField
from tests.utils import assert_nested_subdict

from apps.files import factories

pytestmark = [pytest.mark.django_db, pytest.mark.file]


def test_files_create(admin_client, ida_file_json):
    res = admin_client.post(
        "/v3/files?include_nulls=true",
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
            "published": None,
            "characteristics": None,
            "characteristics_extension": None,
            "pas_compatible_file": None,
            "non_pas_compatible_file": None,
        },
        res.json(),
        check_all_keys_equal=True,
    )


def test_files_create_twice(admin_client, ida_file_json):
    res = admin_client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 400
    assert "pathname" in res.json()


def test_files_create_and_put(admin_client, ida_file_json):
    res = admin_client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    del ida_file_json["size"]
    res = admin_client.put(
        f"/v3/files/{res.data['id']}", ida_file_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["size"] == 0


def test_files_create_and_patch(admin_client, ida_file_json):
    res = admin_client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["size"] == 1024
    patch_json = {"size": 123456}
    res = admin_client.patch(
        f"/v3/files/{res.data['id']}", patch_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["size"] == 123456


def test_files_create_missing_identifier(admin_client, ida_file_json):
    del ida_file_json["storage_identifier"]
    res = admin_client.post(
        "/v3/files",
        ida_file_json,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.data["storage_identifier"][0] == "Field is required for storage_service 'ida'"


def test_files_create_pas_compatible_file(ida_client, ida_file_json):
    file = factories.FileFactory()
    res = ida_client.post(
        "/v3/files",
        {
            **ida_file_json,
            "pas_compatible_file": file.id,
        },
        content_type="application/json",
    )
    assert res.status_code == 201, res.data
    assert res.json()["pas_compatible_file"] == str(file.id)
    file.refresh_from_db()
    assert str(file.non_pas_compatible_file.id) == res.json()["id"]


def test_files_create_pas_compatible_file_non_existent(ida_client):
    file = factories.FileFactory()
    res = ida_client.patch(
        f"/v3/files/{file.id}",
        {"pas_compatible_file": "00000000-0000-0000-0000-000000000000"},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "object does not exist" in res.json()["pas_compatible_file"][0]


def test_files_patch_pas_compatible_file_self(ida_client):
    file = factories.FileFactory()
    res = ida_client.patch(
        f"/v3/files/{file.id}",
        {"pas_compatible_file": file.id},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"pas_compatible_file": "File cannot refer to itself."}
