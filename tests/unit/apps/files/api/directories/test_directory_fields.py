import pytest
from tests.utils import assert_nested_subdict, matchers

from apps.core import factories
from apps.files.views.directory_view import DirectoryCommonQueryParams

pytestmark = [pytest.mark.django_db, pytest.mark.file]


def test_directory_field_values(admin_client, file_tree_b):
    dataset = factories.PublishedDatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        storage=file_tree_b["storage"],
        files=file_tree_b["files"].values(),
    )
    res = admin_client.get(
        "/v3/directories",
        {
            "include_nulls": True,
            "pagination": False,
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {
                "storage_service": "ida",
                "csc_project": "project_x",
                "name": "",
                "pathname": "/",
                "file_count": 3,
                "size": 3210,
                "created": file_tree_b["files"]["/rootfile.txt"].modified,
                "modified": file_tree_b["files"]["/dir/last"].modified,
                "parent_url": None,
            },
            "directories": [
                {
                    "storage_service": "ida",
                    "csc_project": "project_x",
                    "name": "dir",
                    "pathname": "/dir/",
                    "file_count": 2,
                    "size": 3200,
                    "created": file_tree_b["files"]["/dir/first"].modified,
                    "modified": file_tree_b["files"]["/dir/last"].modified,
                    "url": (
                        "http://testserver/v3/directories"
                        "?include_nulls=True&pagination=False&csc_project=project_x&storage_service=ida&path=/dir/"
                    ),
                }
            ],
            "files": [
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "pathname": "/rootfile.txt",
                    "filename": "rootfile.txt",
                    "size": 10,
                    "csc_project": "project_x",
                    "storage_service": "ida",
                    "storage_identifier": "file_rootfile.txt_00000000-0000-0000-0000-000000000000",
                    "checksum": "md5:f00f",
                    "modified": file_tree_b["files"]["/rootfile.txt"].modified,
                    "frozen": file_tree_b["files"]["/rootfile.txt"].frozen,
                    "removed": None,
                    "user": None,
                    "published": matchers.DateTimeStr(),
                    "characteristics": None,
                    "characteristics_extension": None,
                    "pas_compatible_file": None,
                    "non_pas_compatible_file": None,
                    "pas_process_running": False,
                }
            ],
        },
        res.data,
        check_all_keys_equal=True,
    )


def test_directory_file_fields(admin_client, file_tree_b):
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "file_fields": "pathname,size",
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "pathname": "/rootfile.txt",  # computed from other fields
            "size": 10,
        },
        res.data["files"][0],
        check_all_keys_equal=True,
    )


def test_directory_directory_fields(admin_client, file_tree_b):
    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "directory_fields": "name,pathname,file_count,size",
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "name": "dir",
            "pathname": "/dir/",
            "size": 3200,
            "file_count": 2,
        },
        res.data["directories"][0],
        check_all_keys_equal=True,
    )


def test_directory_all_directory_fields(admin_client, file_tree_b):
    fields = set(DirectoryCommonQueryParams.allowed_directory_fields)
    fields = fields - {"dataset_metadata"}  # metadata not available without dataset

    res = admin_client.get(
        "/v3/directories",
        {
            "pagination": False,
            "count_published": True,
            "directory_fields": ",".join(DirectoryCommonQueryParams.allowed_directory_fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["directories"][0]) == fields
    assert "dataset_metadata" not in res.data["directories"][0]


def test_directory_all_file_fields(admin_client, file_tree_b):
    fields = set(DirectoryCommonQueryParams.allowed_file_fields)
    fields = fields - {"dataset_metadata"}  # metadata not available without dataset
    res = admin_client.get(
        "/v3/directories",
        {
            "include_nulls": True,
            "pagination": False,
            "file_fields": ",".join(fields),
            **file_tree_b["params"],
        },
    )
    assert res.status_code == 200
    assert set(res.data["files"][0]) == set(fields)
