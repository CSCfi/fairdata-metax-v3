import pytest
from django.db import transaction
from rest_framework.fields import UUIDField
from tests.utils import assert_nested_subdict

from apps.common.locks import select_queryset_for_update
from apps.files import factories
from apps.files.models import File

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
            "pas_process_running": False,
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


def test_files_create_pas_compatible_file(pas_client, ida_file_json):
    file = factories.FileFactory()
    res = pas_client.post(
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


def test_files_create_pas_compatible_file_non_existent(pas_client):
    file = factories.FileFactory()
    res = pas_client.patch(
        f"/v3/files/{file.id}",
        {"pas_compatible_file": "00000000-0000-0000-0000-000000000000"},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "object does not exist" in res.json()["pas_compatible_file"][0]


def test_files_patch_pas_compatible_file_self(pas_client):
    file = factories.FileFactory()
    res = pas_client.patch(
        f"/v3/files/{file.id}",
        {"pas_compatible_file": file.id},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"pas_compatible_file": "File cannot refer to itself."}


@pytest.mark.parametrize(
    "client,should_work", [("admin_client", True), ("pas_client", True), ("ida_client", False)]
)
def test_files_create_and_update_locked_by_pas(
    request, client, admin_client, should_work, ida_file_json
):
    client = request.getfixturevalue(client)  # Select client fixture based on parameter
    ida_file_json["pas_process_running"] = True
    res = admin_client.post("/v3/files", ida_file_json, content_type="application/json")
    assert res.status_code == 201

    url = f'/v3/files/{res.data["id"]}'
    res = client.patch(url, {"size": 123}, content_type="application/json")
    if should_work:
        assert res.status_code == 200
    else:
        assert res.status_code == 423
        assert "Only PAS service is allowed to modify the file" in res.json()["detail"]

    # Request should be successful after lock is removed
    res = admin_client.patch(url, {"pas_process_running": False}, content_type="application/json")
    assert res.status_code == 200
    res = client.patch(url, {"size": 345}, content_type="application/json")
    assert res.status_code == 200


@pytest.mark.parametrize(
    "client,should_work", [("admin_client", True), ("pas_client", True), ("ida_client", False)]
)
def test_files_create_permissions_pas_process_running(request, client, should_work, ida_file_json):
    client = request.getfixturevalue(client)  # Select client fixture based on parameter
    ida_file_json["pas_process_running"] = True
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    if should_work:
        assert res.status_code == 201
    else:
        assert res.status_code == 400
        assert "Only PAS service is allowed to set" in res.json()["pas_process_running"]


@pytest.mark.parametrize(
    "client,should_work", [("admin_client", True), ("pas_client", True), ("ida_client", False)]
)
def test_files_create_permissions_pas_compatible_file(request, client, should_work, ida_file_json):
    pas_compatible_file = factories.FileFactory()
    client = request.getfixturevalue(client)  # Select client fixture based on parameter
    ida_file_json["pas_compatible_file"] = pas_compatible_file.id
    res = client.post("/v3/files", ida_file_json, content_type="application/json")
    if should_work:
        assert res.status_code == 201
    else:
        assert res.status_code == 400
        assert "Only PAS service is allowed to set" in res.json()["pas_compatible_file"]


@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
def test_files_lock_for_update(admin_client):
    file1 = factories.FileFactory()
    file2 = factories.FileFactory()

    # Lock file1 in transaction using extra_connection
    with transaction.atomic(using="extra_connection"):
        select_queryset_for_update(File.objects.using("extra_connection").filter(id=file1.id))

        # File updates for the locked file should fail
        res = admin_client.patch(
            f"/v3/files/{file1.id}", {"size": 123}, content_type="application/json"
        )
        assert res.status_code == 423
        assert res.json() == {"detail": "The file is locked for update by another request."}

        res = admin_client.delete(f"/v3/files/{file1.id}", content_type="application/json")
        assert res.status_code == 423
        assert res.json() == {"detail": "The file is locked for update by another request."}

        # The other file should not be locked
        res = admin_client.patch(
            f"/v3/files/{file2.id}", {"size": 123}, content_type="application/json"
        )
        assert res.status_code == 200

    # After the extra_connection transaction ends, file1 is no longer locked
    res = admin_client.patch(
        f"/v3/files/{file1.id}", {"size": 123}, content_type="application/json"
    )
    assert res.status_code == 200

    res = admin_client.delete(f"/v3/files/{file1.id}", content_type="application/json")
    assert res.status_code == 204
