from typing import Union
from uuid import UUID

import pytest
from rest_framework.reverse import reverse

from apps.core import factories
from apps.core.models import Dataset
from apps.files.factories import create_project_with_files
from apps.users.models import MetaxUser


@pytest.fixture
def user():
    user, created = MetaxUser.objects.get_or_create(
        username="test_user", first_name="Teppo", last_name="Testaaja", is_hidden=False
    )
    user.set_password("teppo")
    user.save()
    return user


@pytest.fixture
def data_urls():
    """Return urls related to dataset data."""

    def f(dataset: Union[Dataset, UUID, str]):
        dataset_id = dataset.id if isinstance(dataset, Dataset) else dataset
        kwargs = {"dataset_id": dataset_id}
        return {
            "dataset": reverse("dataset-detail", kwargs={"pk": dataset_id}),
            "files": reverse("dataset-files-list", kwargs=kwargs),
            "directories": reverse("dataset-directories-list", kwargs=kwargs),
        }

    return f


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
        file_args={"*": {"size": 1024}},
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
        file_args={"*": {"size": 1024}},
    )


@pytest.fixture
def dataset_with_files(file_tree):
    dataset = factories.DatasetFactory()
    storage = next(iter(file_tree["files"].values())).storage
    file_set = factories.FileSetFactory(dataset=dataset, storage=storage)
    file_set.files.set(
        [
            file_tree["files"]["/dir1/file.csv"],
            file_tree["files"]["/dir2/a.txt"],
            file_tree["files"]["/dir2/b.txt"],
            file_tree["files"]["/dir2/subdir/file1.txt"],
        ]
    )
    return dataset
