"""Tests for listing dataset files with /dataset/<id>/files endpoint."""

import pytest
from tests.utils import assert_nested_subdict

from apps.core import factories

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_dataset_files(admin_client, dataset_with_files, data_urls):
    url = data_urls(dataset_with_files)["files"]
    res = admin_client.get(url)
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/dir1/file.csv"},
                {"pathname": "/dir2/a.txt"},
                {"pathname": "/dir2/b.txt"},
                {"pathname": "/dir2/subdir/file1.txt"},
            ]
        },
        res.data,
        check_list_length=True,
    )


def test_dataset_files_single_file(admin_client, dataset_with_files, data_urls):
    file_id = dataset_with_files.file_set.files.get(filename="file.csv").id
    url = f'{data_urls(dataset_with_files)["files"]}/{file_id}'
    res = admin_client.get(url)
    assert res.status_code == 200
    assert_nested_subdict(
        {"pathname": "/dir1/file.csv"},
        res.data,
        check_list_length=True,
    )


def test_dataset_files_no_pagination(admin_client, dataset_with_files, data_urls):
    url = data_urls(dataset_with_files)["files"]
    res = admin_client.get(url, {"pagination": "false"})
    assert res.status_code == 200
    assert_nested_subdict(
        [
            {"pathname": "/dir1/file.csv"},
            {"pathname": "/dir2/a.txt"},
            {"pathname": "/dir2/b.txt"},
            {"pathname": "/dir2/subdir/file1.txt"},
        ],
        res.data,
        check_list_length=True,
    )


def test_dataset_directories(admin_client, dataset_with_files, data_urls):
    url = data_urls(dataset_with_files)["directories"]
    res = admin_client.get(
        url,
        {
            "pagination": False,
            "path": "/dir2/",
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "directory": {
                "name": "dir2",
                "file_count": 3,
                "size": 3 * 1024,
            },
            "directories": [
                {"name": "subdir", "file_count": 1, "size": 1024},
            ],
            "files": [
                {"filename": "a.txt"},
                {"filename": "b.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


def test_dataset_directories_no_files(admin_client, dataset_with_files, data_urls):
    another_dataset = factories.DatasetFactory()
    url = data_urls(another_dataset)["directories"]
    res = admin_client.get(
        url,
        {
            "pagination": False,
        },
    )
    assert res.status_code == 404


def test_dataset_file_set_no_files(admin_client, dataset_with_files, data_urls):
    another_dataset = factories.DatasetFactory()
    url = data_urls(another_dataset)["dataset"]
    res = admin_client.get(
        url,
        {
            "pagination": False,
        },
    )
    assert res.data.get("fileset") is None
