import pytest

from tests.utils import assert_nested_subdict
from apps.core import factories


@pytest.fixture
def file_tree_with_datasets(file_tree_a):
    dataset_a = factories.DatasetFactory()
    dataset_a.files.set(
        [
            file_tree_a["files"]["/dir/sub1/file1.csv"],
            file_tree_a["files"]["/dir/sub1/file2.csv"],
            file_tree_a["files"]["/dir/sub6/file.csv"],
            file_tree_a["files"]["/dir/c.txt"],
            file_tree_a["files"]["/dir/d.txt"],
        ]
    )
    file_tree_a["dataset_a"] = dataset_a

    dataset_b = factories.DatasetFactory()
    dataset_b.files.set(
        [
            file_tree_a["files"]["/dir/sub4/file.csv"],
            file_tree_a["files"]["/dir/sub6/file.csv"],
        ]
    )
    file_tree_a["dataset_b"] = dataset_b

    dataset_c = factories.DatasetFactory()
    file_tree_a["dataset_c"] = dataset_c
    return file_tree_a


@pytest.mark.django_db
def test_directory_dataset_a(client, file_tree_with_datasets):
    res = client.get(
        "/rest/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_a"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "directory_name": "dir",
                "file_count": 5,
                "byte_size": 5 * 1024,
            },
            "directories": [
                {"directory_name": "sub1", "file_count": 2, "byte_size": 2 * 1024},
                {"directory_name": "sub6", "file_count": 1, "byte_size": 1024},
            ],
            "files": [
                {"file_name": "c.txt"},
                {"file_name": "d.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_dataset_b(client, file_tree_with_datasets):
    res = client.get(
        "/rest/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_b"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "directory_name": "dir",
                "file_count": 2,
                "byte_size": 2 * 1024,
            },
            "directories": [
                {"directory_name": "sub4", "file_count": 1, "byte_size": 1024},
                {"directory_name": "sub6", "file_count": 1, "byte_size": 1024},
            ],
            "files": [],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_directory_dataset_no_files_dataset(client, file_tree_with_datasets):
    dataset = factories.DatasetFactory()
    res = client.get(
        "/rest/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_c"].id,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.json() == {"directories": [], "files": []}


@pytest.mark.django_db
def test_directory_exclude_dataset_a(client, file_tree_with_datasets):
    res = client.get(
        "/rest/v3/directories",
        {
            "dataset": file_tree_with_datasets["dataset_a"].id,
            "exclude_dataset": True,
            "pagination": False,
            "path": "/dir",
            **file_tree_with_datasets["params"],
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "directory_name": "dir",
                "file_count": 10,
                "byte_size": 10 * 1024,
            },
            "directories": [
                {
                    "directory_name": "sub1",
                    "file_count": 1,
                    "byte_size": 1 * 1024,
                },  # 1 file not yet in dataset
                {"directory_name": "sub2", "file_count": 1, "byte_size": 1 * 1024},
                {"directory_name": "sub3", "file_count": 1, "byte_size": 1 * 1024},
                {"directory_name": "sub4", "file_count": 1, "byte_size": 1 * 1024},
                {"directory_name": "sub5", "file_count": 2, "byte_size": 2 * 1024},
            ],
            "files": [
                {"file_name": "a.txt"},
                {"file_name": "b.txt"},
                {"file_name": "e.txt"},
                {"file_name": "f.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )
