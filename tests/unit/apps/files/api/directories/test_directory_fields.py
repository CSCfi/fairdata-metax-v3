import pytest
from tests.utils import assert_nested_subdict

from apps.core.models import FileSetDirectoryMetadata
from apps.files.models import FileStorage
from apps.files.views.directory_view import DirectoryCommonQueryParams


@pytest.mark.django_db
def test_directory_field_values(client, file_tree_b):
    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "storage_service": "ida",
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
                    "storage_service": "ida",
                    "project_identifier": "project_x",
                    "directory_name": "dir",
                    "directory_path": "/dir/",
                    "file_count": 2,
                    "byte_size": 3200,
                    "created": file_tree_b["files"]["/dir/first"].created,
                    "modified": file_tree_b["files"]["/dir/last"].modified,
                    "url": "http://testserver/v3/directories?pagination=False&project_identifier=project_x&storage_service=ida&path=/dir/",
                }
            ],
            "files": [
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "file_path": "/rootfile.txt",
                    "file_name": "rootfile.txt",
                    "byte_size": 10,
                    "project_identifier": "project_x",
                    "storage_service": "ida",
                    "file_storage_pathname": None,
                    "file_storage_identifier": "file_rootfile.txt_00000000-0000-0000-0000-000000000000",
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
        "/v3/directories",
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
        "/v3/directories",
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
    fields = set(DirectoryCommonQueryParams.allowed_directory_fields)
    fields = fields - {"dataset_metadata"}  # metadata not available without dataset

    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            "directory_fields": ",".join(DirectoryCommonQueryParams.allowed_directory_fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["directories"][0]) == fields
    assert "dataset_metadata" not in res.data["directories"][0]


@pytest.mark.django_db
def test_directory_all_file_fields(client, file_tree_b):
    fields = set(DirectoryCommonQueryParams.allowed_file_fields)
    fields = fields - {"dataset_metadata"}  # metadata not available without dataset
    res = client.get(
        "/v3/directories",
        {
            "pagination": False,
            "file_fields": ",".join(fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["files"][0]) == set(fields)
