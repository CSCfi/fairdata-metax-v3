import pytest
from rest_framework.fields import DateTimeField, UUIDField
from tests.utils import assert_nested_subdict

from apps.files import factories
from apps.files.serializers import FileSerializer


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
            "file_name": "file.pdf",
            "directory_path": "/some/file/path/",
            "created": DateTimeField(),
            "modified": DateTimeField(),
            "id": UUIDField(),
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
    assert "file_path" in res.json()
