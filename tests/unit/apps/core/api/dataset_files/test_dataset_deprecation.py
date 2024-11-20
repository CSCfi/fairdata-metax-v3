"""Tests for updating dataset files with /dataset/<id>/files endpoint."""

from typing import Dict

import pytest
from tests.utils import assert_nested_subdict, matchers

from apps.core import factories

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def dataset_to_deprecate(deep_file_tree):
    dataset = factories.PublishedDatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        storage=deep_file_tree["storage"],
        files=[
            deep_file_tree["files"]["/dir2/subdir1/file3.txt"],
            deep_file_tree["files"]["/dir2/subdir2/file1.txt"],
        ],
    )
    return dataset


@pytest.fixture
def dataset_to_not_deprecate(deep_file_tree):
    dataset = factories.PublishedDatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        storage=deep_file_tree["storage"],
        files=[
            # Deleting file3.txt should not affect this dataset
            deep_file_tree["files"]["/dir2/subdir2/file1.txt"],
        ],
    )
    return dataset


def test_dataset_deprecation_delete_single(
    admin_client, deep_file_tree, dataset_to_deprecate, dataset_to_not_deprecate
):
    res = admin_client.delete(
        f'/v3/files/{deep_file_tree["files"]["/dir2/subdir1/file3.txt"].id}',
        content_type="application/json",
    )
    assert res.status_code == 204
    dataset_to_deprecate.refresh_from_db()
    dataset_to_not_deprecate.refresh_from_db()
    assert dataset_to_deprecate.deprecated is not None
    assert dataset_to_not_deprecate.deprecated is None


def test_dataset_deprecation_delete_many(
    admin_client, deep_file_tree, dataset_to_deprecate, dataset_to_not_deprecate
):
    res = admin_client.post(
        "/v3/files/delete-many",
        [{"id": deep_file_tree["files"]["/dir2/subdir1/file3.txt"].id}],
        content_type="application/json",
    )
    assert res.status_code == 200
    dataset_to_deprecate.refresh_from_db()
    dataset_to_not_deprecate.refresh_from_db()
    assert dataset_to_deprecate.deprecated is not None
    assert dataset_to_not_deprecate.deprecated is None


def test_dataset_deprecation_delete_list(admin_client, deep_file_tree, dataset_to_deprecate):
    res = admin_client.delete(
        f'/v3/files?csc_project={deep_file_tree["storage"].csc_project}',
        content_type="application/json",
    )
    assert res.status_code == 200
    dataset_to_deprecate.refresh_from_db()
    assert dataset_to_deprecate.deprecated is not None
