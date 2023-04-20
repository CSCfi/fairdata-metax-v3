import json
import logging
import os

import pytest
from rest_framework.reverse import reverse

from apps.files import factories

logger = logging.getLogger(__name__)

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"


def load_test_json(filename):
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def filestorage_a_json():
    return load_test_json("filestorage_a.json")


@pytest.fixture
def filestorage_b_json():
    return load_test_json("filestorage_b.json")


@pytest.fixture
def filestorage_c_json():
    return load_test_json("filestorage_c.json")


@pytest.fixture
def filestorage_a_updated_json():
    return load_test_json("filestorage_a_updated.json")


@pytest.fixture
def filestorage_a_invalid_json():
    return load_test_json("filestorage_a_invalid.json")


@pytest.fixture(scope="module")
def file_storage_list_url():
    return reverse("storage-list")


@pytest.fixture
def post_filestorage_payloads_a_b_c(
    client, filestorage_a_json, filestorage_b_json, filestorage_c_json, file_storage_list_url
):
    res1 = client.post(file_storage_list_url, filestorage_a_json, content_type="application/json")
    res2 = client.post(file_storage_list_url, filestorage_b_json, content_type="application/json")
    res3 = client.post(file_storage_list_url, filestorage_c_json, content_type="application/json")
    return res1, res2, res3


@pytest.fixture
def file_tree_a() -> dict:
    return factories.create_project_with_files(
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/sub1/file2.csv",
            "/dir/sub1/file3.csv",
            "/dir/sub2/file.csv",
            "/dir/sub3/file.csv",
            "/dir/sub4/file.csv",
            "/dir/sub5/file1.csv",
            "/dir/sub5/file2.csv",
            "/dir/sub6/file.csv",
            "/dir/a.txt",
            "/dir/b.txt",
            "/dir/c.txt",
            "/dir/d.txt",
            "/dir/e.txt",
            "/dir/f.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"byte_size": 1024}},
    )


@pytest.fixture
def file_tree_b() -> dict:
    return factories.create_project_with_files(
        file_storage="test-file-storage-a",
        project_identifier="project_x",
        file_paths=[
            "/dir/first",
            "/dir/last",
            "/rootfile.txt",
        ],
        file_args={
            "*": {
                "checksum": {
                    "algorithm": "md5",
                    "checked": "2023-01-01T01:00:00Z",
                    "value": "f00f",
                },
                "file_modified": "2022-01-01T12:00:00Z",
                "date_frozen": "2022-01-02T12:00:00Z",
                "date_uploaded": "2022-01-03T12:00:00Z",
            },
            "/dir/first": {
                "id": "00000000-0000-0000-0000-000000000001",
                "created": "2023-01-01T10:00:00Z",
                "modified": "2023-01-01T13:00:00Z",
                "byte_size": 200,
            },
            "/dir/last": {
                "id": "00000000-0000-0000-0000-000000000002",
                "created": "2023-01-01T12:00:00Z",
                "modified": "2023-01-01T22:00:00Z",
                "byte_size": 3000,
            },
            "/rootfile.txt": {
                "id": "00000000-0000-0000-0000-000000000000",
                "created": "2023-01-01T05:00:00Z",
                "modified": "2023-01-01T12:00:00Z",
                "byte_size": 10,
            },
        },
    )
