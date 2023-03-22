"""Tests for viewing and updating dataset files with files parameter of /dataset and /dataset/<id> endpoints."""

import pytest
from tests.utils import assert_nested_subdict


@pytest.fixture
def dataset_json_with_files(deep_file_tree, data_catalog):
    return {
        "data_catalog": data_catalog.id,
        "title": {"en": "Test dataset"},
        "files": {
            **deep_file_tree["params"],
            "directory_actions": [
                {
                    "directory_path": "/dir1/",
                    "dataset_metadata": {"title": "directory"},
                }
            ],
            "file_actions": [
                {
                    "id": deep_file_tree["files"]["/rootfile.txt"].id,
                    "dataset_metadata": {"title": "file"},
                }
            ],
        },
    }


@pytest.fixture
def dataset_json_with_no_files(deep_file_tree, data_catalog):
    return {
        "data_catalog": data_catalog.id,
        "title": {"en": "Test dataset"},
    }


@pytest.mark.django_db
def test_dataset_post_dataset_with_files(client, deep_file_tree, dataset_json_with_files):
    res = client.post(
        f"/rest/v3/dataset",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.data["files"]["added_files_count"] == 3
    assert res.data["files"]["removed_files_count"] == 0
    assert res.data["files"]["total_files_count"] == 3

    res = client.get(f"/rest/v3/dataset/{res.data['id']}/directories?pagination=false")
    assert_nested_subdict(
        {
            "directories": [
                {"directory_path": "/dir1/", "dataset_metadata": {"title": "directory"}},
            ],
            "files": [{"file_path": "/rootfile.txt", "dataset_metadata": {"title": "file"}}],
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_get_dataset_with_files(client, deep_file_tree, dataset_json_with_files):
    res = client.post(
        f"/rest/v3/dataset",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = client.get(f"/rest/v3/dataset/{res.data['id']}")
    assert res.status_code == 200
    assert res.data["files"] == {
        # no added_files_count or removed_files_count should be present for GET
        "file_storage": deep_file_tree["params"]["file_storage"],
        "project_identifier": deep_file_tree["params"]["project_identifier"],
        "total_files_count": 3,
        "total_files_byte_size": 3 * 1024,
    }


@pytest.mark.django_db
def test_dataset_get_dataset_with_no_files(client, deep_file_tree, dataset_json_with_no_files):
    res = client.post(
        f"/rest/v3/dataset",
        dataset_json_with_no_files,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = client.get(f"/rest/v3/dataset/{res.data['id']}")
    assert res.status_code == 200
    assert "files" not in res.data  # no files dict should be present if dataset has no files


@pytest.mark.django_db
def test_dataset_modify_dataset_with_files(client, deep_file_tree, dataset_json_with_files):
    res = client.post(
        f"/rest/v3/dataset",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201
    dataset_id = res.data["id"]

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [{"directory_path": "/dir1/", "action": "remove"}],
        "file_actions": [{"id": deep_file_tree["files"]["/dir3/sub1/file.txt"].id}],
    }

    dataset_json = {k: v for k, v in res.data.items() if v != None}
    res = client.put(
        f"/rest/v3/dataset/{dataset_id}",
        {**dataset_json, "files": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["files"]["added_files_count"] == 1
    assert res.data["files"]["removed_files_count"] == 2
    assert res.data["files"]["total_files_count"] == 2

    res = client.get(f"/rest/v3/dataset/{dataset_id}/directories?pagination=false")
    assert_nested_subdict(
        {
            "directories": [
                {"directory_path": "/dir3/"},
            ],
            "files": [{"file_path": "/rootfile.txt", "dataset_metadata": {"title": "file"}}],
        },
        res.json(),
    )