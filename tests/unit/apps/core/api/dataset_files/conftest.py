import pytest

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
def deep_file_tree() -> dict:
    return create_project_with_files(
        file_paths=[
            "/dir1/file.csv",
            "/dir1/sub/file.csv",
            "/dir2/a.txt",
            "/dir2/subdir1/file1.txt",
            "/dir2/subdir1/file2.txt",
            "/dir2/subdir1/file3.txt",
            "/dir2/subdir2/file1.txt",
            "/dir2/subdir2/file2.txt",
            "/dir2/subdir2/file3.txt",
            "/dir2/subdir2/subsub/subsubsub1/file.txt",
            "/dir2/subdir2/subsub/subsubsub2/file1.txt",
            "/dir2/subdir2/subsub/subsubsub2/file2.txt",
            "/dir3/sub1/file.txt",
            "/dir3/sub2/file.txt",
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
