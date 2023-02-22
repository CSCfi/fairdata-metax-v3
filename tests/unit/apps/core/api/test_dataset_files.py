import pytest
from tests.utils import assert_nested_subdict

from apps.core import factories
from apps.files.factories import create_project_with_files


@pytest.fixture
def file_tree() -> dict:
    return create_project_with_files(
        file_paths=[
            "/dir1/file.csv",
            "/dir2/a.txt",
            "/dir2/b.txt",
            "/dir2/c.txt",
            "/dir2/subdir/file1.txt",
            "/dir2/subdir/file2.txt",
            "/dir3/file.pdf",
            "/rootfile.txt",
        ],
        file_args={"*": {"byte_size": 1024}},
    )


@pytest.fixture
def dataset_with_files(file_tree):
    dataset = factories.DatasetFactory()
    dataset.files.set(
        [
            file_tree["files"]["/dir1/file.csv"],
            file_tree["files"]["/dir2/a.txt"],
            file_tree["files"]["/dir2/b.txt"],
            file_tree["files"]["/dir2/subdir/file1.txt"],
        ]
    )
    unrelated_dataset = factories.DatasetFactory()
    unrelated_dataset.files.set(
        [  # this should not affect the first dataset at all
            file_tree["files"]["/dir1/file.csv"],
            file_tree["files"]["/dir2/b.txt"],
        ]
    )
    return dataset


@pytest.mark.django_db
def test_dataset_files(client, dataset_with_files):
    res = client.get(f"/rest/v3/dataset/{dataset_with_files.id}/files")
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/dir1/file.csv"},
                {"file_path": "/dir2/a.txt"},
                {"file_path": "/dir2/b.txt"},
                {"file_path": "/dir2/subdir/file1.txt"},
            ]
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_dataset_directories(client, dataset_with_files):

    res = client.get(
        f"/rest/v3/dataset/{dataset_with_files.id}/directories",
        {
            "pagination": False,
            "path": "/dir2/",
        },
    )
    assert res.status_code == 200
    assert_nested_subdict(
        {
            "parent_directory": {
                "directory_name": "dir2",
                "file_count": 3,
                "byte_size": 3 * 1024,
            },
            "directories": [
                {"directory_name": "subdir", "file_count": 1, "byte_size": 1024},
            ],
            "files": [
                {"file_name": "a.txt"},
                {"file_name": "b.txt"},
            ],
        },
        res.data,
        check_list_length=True,
    )


@pytest.mark.django_db
def test_dataset_directories_no_files(client, dataset_with_files):
    another_dataset = factories.DatasetFactory()
    res = client.get(
        f"/rest/v3/dataset/{another_dataset.id}/directories",
        {
            "pagination": False,
        },
    )
    assert res.status_code == 404
