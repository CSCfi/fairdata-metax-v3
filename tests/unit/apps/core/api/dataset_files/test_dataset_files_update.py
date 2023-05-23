"""Tests for updating dataset files with /dataset/<id>/files endpoint."""

from typing import Dict

import pytest
from tests.utils import assert_nested_subdict

from apps.core import factories


@pytest.mark.django_db
def test_dataset_files_post_empty(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "file_actions": [],
        "directory_actions": [],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 0
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 0
    assert res.data["total_files_byte_size"] == 0

    res = client.get(f"/v3/dataset/{dataset.id}/files")
    assert res.status_code == 200
    assert res.json()["count"] == 0

    res = client.get(f"/v3/dataset/{dataset.id}/directories")
    assert res.status_code == 404  # no storage project exists for dataset


@pytest.mark.django_db
def test_dataset_files_post(client, deep_file_tree):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"directory_path": "/dir2/"},
            {
                "directory_path": "/dir2/subdir2/",
                "action": "remove",
            },
            {"directory_path": "/dir2/subdir2/subsub/"},
            {
                "directory_path": "/dir2/subdir2/subsub/subsubsub2/",
                "action": "remove",
            },
        ],
        "file_actions": [
            {"id": deep_file_tree["files"]["/dir1/sub/file.csv"].id},
            {"id": deep_file_tree["files"]["/rootfile.txt"].id},
            {
                "id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id,
                "action": "remove",
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 7
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 7
    res = client.get(f"/v3/dataset/{dataset.id}/files")

    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/rootfile.txt"},
                {"file_path": "/dir1/sub/file.csv"},
                {"file_path": "/dir2/a.txt"},
                {"file_path": "/dir2/subdir1/file1.txt"},
                {"file_path": "/dir2/subdir1/file2.txt"},
                {"file_path": "/dir2/subdir1/file3.txt"},
                {"file_path": "/dir2/subdir2/subsub/subsubsub1/file.txt"},
            ]
        },
        res.json(),
    )


@pytest.fixture
def dataset_with_metadata(client, deep_file_tree) -> Dict:
    dataset = factories.DatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"directory_path": "/dir2/subdir1/", "dataset_metadata": {"title": "directory title"}},
        ],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id,
                "action": "update",
                "dataset_metadata": {"title": "file title"},
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    return dataset


@pytest.mark.django_db
def test_dataset_files_post_metadata_get_files(client, dataset_with_metadata):
    dataset_id = dataset_with_metadata.id
    res = client.get(f"/v3/dataset/{dataset_id}/files")
    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/dir2/subdir1/file1.txt"},
                {
                    "file_path": "/dir2/subdir1/file2.txt",
                    "dataset_metadata": {"title": "file title"},
                },
                {"file_path": "/dir2/subdir1/file3.txt"},
            ],
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_post_metadata_get_directories(client, dataset_with_metadata):
    dataset_id = dataset_with_metadata.id
    res = client.get(f"/v3/dataset/{dataset_id}/directories?path=/dir2/subdir1/&pagination=false")
    assert_nested_subdict(
        {
            "parent_directory": {
                "directory_name": "subdir1",
                "dataset_metadata": {"title": "directory title"},
            },
            "files": [
                {"file_path": "/dir2/subdir1/file1.txt"},
                {
                    "file_path": "/dir2/subdir1/file2.txt",
                    "dataset_metadata": {"title": "file title"},
                },
                {"file_path": "/dir2/subdir1/file3.txt"},
            ],
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_post_multiple_metadata_updates(client, deep_file_tree):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "action": "add",
                "dataset_metadata": {"title": "title 1"},
            },
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "action": "update",
                "dataset_metadata": {"title": "title 2"},
            },
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "action": "remove",
                "dataset_metadata": {"title": "metadata for remove action is ignored"},
            },
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "action": "add",
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    res = client.get(f"/v3/dataset/{dataset.id}/files")

    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/rootfile.txt", "dataset_metadata": {"title": "title 2"}},
            ]
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_post_remove_file_metadata(client, deep_file_tree):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "dataset_metadata": {"title": "title"},
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = client.get(f"/v3/dataset/{dataset.id}/files")
    assert "dataset_metadata" in res.data["results"][0]

    # remove metadata by setting it to None
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "action": "update",
                "dataset_metadata": None,
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(f"/v3/dataset/{dataset.id}/files")
    assert res.data["results"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_post_remove_directory_metadata(client, deep_file_tree):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "directory_path": "/dir1/",
                "dataset_metadata": {"title": "title"},
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = client.get(f"/v3/dataset/{dataset.id}/directories?pagination=false")
    assert "dataset_metadata" in res.data["directories"][0]

    # remove metadata by setting it to None
    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "directory_path": "/dir1/",
                "action": "update",
                "dataset_metadata": None,
            },
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(f"/v3/dataset/{dataset.id}/directories?pagination=false")
    assert res.data["directories"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_multiple_post_requests(client, deep_file_tree):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"directory_path": "/dir3/"},
            {"directory_path": "/dir2/"},
        ],
        "file_actions": [
            {"id": deep_file_tree["files"]["/dir1/file.csv"].id},
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 13
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 13

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"directory_path": "/dir1/sub/"},
            {"directory_path": "/dir3/", "action": "remove"},
        ],
        "file_actions": [
            {"id": deep_file_tree["files"]["/dir2/subdir1/file1.txt"].id, "action": "remove"},
            {"id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id, "action": "remove"},
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 1
    assert res.data["removed_files_count"] == 4
    assert res.data["total_files_count"] == 10
    res = client.get(f"/v3/dataset/{dataset.id}/files")

    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/dir1/file.csv"},
                {"file_path": "/dir1/sub/file.csv"},
                {"file_path": "/dir2/a.txt"},
                {"file_path": "/dir2/subdir1/file3.txt"},
                {"file_path": "/dir2/subdir2/file1.txt"},
                {"file_path": "/dir2/subdir2/file2.txt"},
                {"file_path": "/dir2/subdir2/file3.txt"},
                {"file_path": "/dir2/subdir2/subsub/subsubsub1/file.txt"},
                {"file_path": "/dir2/subdir2/subsub/subsubsub2/file1.txt"},
                {"file_path": "/dir2/subdir2/subsub/subsubsub2/file2.txt"},
            ]
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_all_metadata_fields(client, deep_file_tree, reference_data):
    dataset = factories.DatasetFactory()

    file_metadata = {
        "title": "File title",
        "description": "File description",
        "file_type": {"url": "http://uri.suomi.fi/codelist/fairdata/file_type/code/text"},
        "use_category": {
            "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/documentation"
        },
    }
    directory_metadata = {
        "title": "Directory title",
        "description": "Directory description",
        "use_category": {"url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"},
    }

    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {"id": deep_file_tree["files"]["/rootfile.txt"].id, "dataset_metadata": file_metadata},
        ],
        "directory_actions": [
            {"directory_path": "/dir1/", "dataset_metadata": directory_metadata}
        ],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(f"/v3/dataset/{dataset.id}/directories?pagination=false")
    assert_nested_subdict(
        {
            "directories": [
                {"directory_path": "/dir1/", "dataset_metadata": directory_metadata},
            ],
            "files": [{"file_path": "/rootfile.txt", "dataset_metadata": file_metadata}],
        },
        res.json(),
    )


# Tests for project_identifier


@pytest.mark.django_db
def test_dataset_files_missing_project_identifier(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    actions = {
        "file_storage": deep_file_tree["params"]["file_storage"],
        "directory_actions": [{"directory_path": "/dir1/"}],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "project_identifier" in res.data


@pytest.mark.django_db
def test_dataset_files_wrong_project_identifier(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    other_project = factories.StorageProjectFactory(
        file_storage=deep_file_tree["storage_project"].file_storage
    )
    actions = {
        "project_identifier": other_project.project_identifier,
        "file_storage": other_project.file_storage_id,
        "directory_actions": [{"directory_path": "/dir1/"}],
        "file_actions": [{"id": deep_file_tree["files"]["/rootfile.txt"].id}],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Directory not found" in str(res.data["directory_path"])
    assert "Files not found" in str(res.data["file.id"])


@pytest.mark.django_db
def test_dataset_files_unknown_project_identifier(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    actions = {
        "project_identifier": "bleh",
        "file_storage": deep_file_tree["params"]["file_storage"],
        "directories": [{"directory_path": "/dir1/"}],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "project_identifier" in str(res.data)


# Tests for file_storage


@pytest.mark.django_db
def test_dataset_files_missing_file_storage(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    actions = {
        "project_identifier": deep_file_tree["params"]["project_identifier"],
        "directory_actions": [{"directory_path": "/dir1/"}],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "file_storage" in res.data


@pytest.mark.django_db
def test_dataset_files_unknown_file_storage(client, deep_file_tree):
    dataset = factories.DatasetFactory()
    actions = {
        "project_identifier": deep_file_tree["params"]["project_identifier"],
        "file_storage": "does_not_exist",
        "directory_actions": [{"directory_path": "/dir1/"}],
    }
    res = client.post(
        f"/v3/dataset/{dataset.id}/files",
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "file_storage" in res.data
