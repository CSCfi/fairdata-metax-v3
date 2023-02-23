import pytest
from tests.utils import assert_nested_subdict

from apps.files.views.directory_view import DirectoryCommonQueryParams


@pytest.mark.django_db
def test_directory_field_values(client, file_tree_b):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "file_storage": "test-file-storage-a",
                "project_identifier": "project_x",
                "directory_name": "",
                "directory_path": "/",
                "file_count": 3,
                "byte_size": 3210,
                "created": file_tree_b["files"]["/rootfile.txt"].created,
                "modified": file_tree_b["files"]["/dir/last"].modified,
                "parent_url": None,
            },
            "directories": [
                {
                    "file_storage": "test-file-storage-a",
                    "project_identifier": "project_x",
                    "directory_name": "dir",
                    "directory_path": "/dir/",
                    "file_count": 2,
                    "byte_size": 3200,
                    "created": file_tree_b["files"]["/dir/first"].created,
                    "modified": file_tree_b["files"]["/dir/last"].modified,
                    "url": "http://testserver/rest/v3/directories?pagination=False&project_identifier=project_x&file_storage=test-file-storage-a&path=/dir/",
                }
            ],
            "files": [
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "file_path": "/rootfile.txt",
                    "file_name": "rootfile.txt",
                    "directory_path": "/",
                    "byte_size": 10,
                    "project_identifier": "project_x",
                    "file_storage": "test-file-storage-a",
                    "checksum": {
                        "algorithm": "md5",
                        "checked": "2023-01-01T03:00:00+02:00",
                        "value": "f00f",
                    },
                    "date_frozen": file_tree_b["files"]["/rootfile.txt"].date_frozen,
                    "file_modified": file_tree_b["files"]["/rootfile.txt"].file_modified,
                    "date_uploaded": file_tree_b["files"]["/rootfile.txt"].date_uploaded,
                    "created": file_tree_b["files"]["/rootfile.txt"].created,
                    "modified": file_tree_b["files"]["/rootfile.txt"].modified,
                }
            ],
        },
        res.data,
        check_all_keys_equal=True,
    )


@pytest.mark.django_db
def test_directory_file_fields(client, file_tree_b):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "file_fields": "file_path,byte_size",
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "file_path": "/rootfile.txt",  # computed from other fields
            "byte_size": 10,
        },
        res.data["files"][0],
        check_all_keys_equal=True,
    )


@pytest.mark.django_db
def test_directory_directory_fields(client, file_tree_b):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "directory_fields": "directory_name,directory_path,file_count,byte_size",
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory_name": "dir",
            "directory_path": "/dir/",
            "byte_size": 3200,
            "file_count": 2,
        },
        res.data["directories"][0],
        check_all_keys_equal=True,
    )


@pytest.mark.django_db
def test_directory_all_directory_fields(client, file_tree_b):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "directory_fields": ",".join(DirectoryCommonQueryParams.allowed_directory_fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["directories"][0]) == set(
        DirectoryCommonQueryParams.allowed_directory_fields
    )


@pytest.mark.django_db
def test_directory_all_file_fields(client, file_tree_b):
    res = client.get(
        "/rest/v3/directories",
        {
            "pagination": False,
            "file_fields": ",".join(DirectoryCommonQueryParams.allowed_file_fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["files"][0]) == set(DirectoryCommonQueryParams.allowed_file_fields)
