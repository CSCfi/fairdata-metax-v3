"""Tests for updating dataset files with /dataset/<id>/files endpoint."""

from typing import Dict

import pytest
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict

from apps.core import factories


@pytest.mark.django_db
def test_dataset_files_post_empty(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "file_actions": [],
        "directory_actions": [],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 0
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 0
    assert res.data["total_files_byte_size"] == 0

    # Dataset should have an empty FileSet
    res = client.get(urls["dataset"])
    assert res.status_code == 200
    assert (
        res.json()["data"]["project_identifier"] == deep_file_tree["params"]["project_identifier"]
    )

    res = client.get(urls["files"])
    assert res.status_code == 200
    assert res.json()["count"] == 0

    res = client.get(urls["directories"])
    assert res.status_code == 200
    assert res.json()["count"] == 0


@pytest.mark.django_db
def test_dataset_files_post_multiple_file_sets(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = deep_file_tree["params"]
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    factories.FileStorageFactory(storage_service="test", project_identifier=None)
    res = client.post(
        urls["file_set"],
        {"storage_service": "test"},
        content_type="application/json",
    )

    assert res.status_code == 400
    assert "Dataset already has a file set" in res.data["storage_service"]


@pytest.mark.django_db
def test_dataset_files_post(client, deep_file_tree, data_urls):
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

    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    assert res.data["added_files_count"] == 6
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 6
    res = client.get(urls["files"])

    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/rootfile.txt"},
                {"file_path": "/dir1/sub/file.csv"},
                {"file_path": "/dir2/a.txt"},
                {"file_path": "/dir2/subdir1/file1.txt"},
                {"file_path": "/dir2/subdir1/file3.txt"},
                {"file_path": "/dir2/subdir2/subsub/subsubsub1/file.txt"},
            ]
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_post_noop_add(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        file_storage=deep_file_tree["file_storage"],
        files=deep_file_tree["files"].values(),
    )

    # file to add file is already in dataset, nothing should happen
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id,
                "action": "add",
            },
        ],
    }

    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 0
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == len(deep_file_tree["files"])


@pytest.mark.django_db
def test_dataset_files_post_noop_remove(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    # file to remove is not in dataset, nothing should happen
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id,
                "action": "remove",
            },
        ],
    }

    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 0
    assert res.data["removed_files_count"] == 0
    assert res.data["total_files_count"] == 0


@pytest.fixture
def dataset_with_metadata(client, deep_file_tree, data_urls) -> Dict:
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

    url = data_urls(dataset)["file_set"]
    res = client.post(
        url,
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    return dataset


@pytest.mark.django_db
def test_dataset_files_post_metadata_get_files(client, dataset_with_metadata, data_urls):
    url = data_urls(dataset_with_metadata)["files"]
    res = client.get(url)
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
def test_dataset_files_post_metadata_get_directories(client, dataset_with_metadata, data_urls):
    url = data_urls(dataset_with_metadata)["directories"]
    res = client.get(url, {"path": "/dir2/subdir1", "pagination": "false"})
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
def test_dataset_files_post_multiple_metadata_updates(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    urls = data_urls(dataset)
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
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    res = client.get(urls["files"])

    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/rootfile.txt", "dataset_metadata": {"title": "title 2"}},
            ]
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_post_update_for_existing_metadata(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    urls = data_urls(dataset)
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "dataset_metadata": {"title": "title 1"},
            },
        ],
        "directory_actions": [
            {
                "directory_path": "/",
                "dataset_metadata": {"title": "root dir"},
            },
        ],
    }
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "dataset_metadata": {"title": "title 2"},
            },
        ],
        "directory_actions": [
            {
                "directory_path": "/",
                "dataset_metadata": {"title": "root dir updated"},
            },
        ],
    }
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(urls["files"])
    assert_nested_subdict(
        {
            "results": [
                {"file_path": "/rootfile.txt", "dataset_metadata": {"title": "title 2"}},
            ]
        },
        res.json(),
    )

    res = client.get(urls["directories"], {"pagination": "false"})
    assert res.data["parent_directory"]["dataset_metadata"]["title"] == "root dir updated"


@pytest.mark.django_db
def test_dataset_files_post_remove_file_metadata(client, deep_file_tree, data_urls):
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
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = client.get(urls["files"])
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
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(urls["files"])
    assert res.data["results"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_post_none_file_metadata(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/rootfile.txt"].id,
                "dataset_metadata": None,
            },
        ],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(urls["files"])
    assert res.data["results"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_post_remove_directory_metadata(client, deep_file_tree, data_urls):
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
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = client.get(urls["directories"], {"pagination": "false"})
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
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(urls["directories"], {"pagination": "false"})
    assert res.data["directories"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_post_none_directory_metadata(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "directory_path": "/dir1/",
                "dataset_metadata": None,
            },
        ],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    res = client.get(urls["directories"], {"pagination": "false"})
    assert res.data["directories"][0]["dataset_metadata"] is None


@pytest.mark.django_db
def test_dataset_files_multiple_post_requests(client, deep_file_tree, data_urls):
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

    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
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
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["added_files_count"] == 1
    assert res.data["removed_files_count"] == 4
    assert res.data["total_files_count"] == 10
    res = client.get(urls["files"])

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
def test_dataset_files_all_metadata_fields(client, deep_file_tree, reference_data, data_urls):
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
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = client.get(urls["directories"], {"pagination": "false"})
    assert_nested_subdict(
        {
            "directories": [
                {"directory_path": "/dir1/", "dataset_metadata": directory_metadata},
            ],
            "files": [{"file_path": "/rootfile.txt", "dataset_metadata": file_metadata}],
        },
        res.json(),
    )


@pytest.mark.django_db
def test_dataset_files_invalid_file_type(client, deep_file_tree, reference_data, data_urls):
    dataset = factories.DatasetFactory()

    file_metadata = {
        "title": "File title",
        "description": "File description",
        "file_type": {"url": "http://uri.suomi.fi/codelist/fairdata/file_type/code/peruna"},
    }
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {"id": deep_file_tree["files"]["/rootfile.txt"].id, "dataset_metadata": file_metadata},
        ],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Invalid values" in res.data["file_type"]


@pytest.mark.django_db
def test_dataset_files_invalid_use_category(client, deep_file_tree, reference_data, data_urls):
    dataset = factories.DatasetFactory()

    file_metadata = {
        "title": "File title",
        "description": "File description",
        "use_category": {
            "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/porkkana"
        },
    }
    actions = {
        **deep_file_tree["params"],
        "file_actions": [
            {"id": deep_file_tree["files"]["/rootfile.txt"].id, "dataset_metadata": file_metadata},
        ],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Invalid values" in res.data["use_category"]


@pytest.mark.django_db
def test_dataset_files_missing_project_identifier(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = {
        "storage_service": deep_file_tree["params"]["storage_service"],
        "directory_actions": [{"directory_path": "/dir1/"}],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "project_identifier" in res.data


@pytest.mark.django_db
def test_dataset_files_wrong_project_identifier(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    other_storage = factories.FileStorageFactory(
        storage_service=deep_file_tree["file_storage"].storage_service
    )
    actions = {
        "project_identifier": other_storage.project_identifier,
        "storage_service": other_storage.storage_service,
        "directory_actions": [{"directory_path": "/dir1/"}],
        "file_actions": [{"id": deep_file_tree["files"]["/rootfile.txt"].id}],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Directory not found" in str(res.data["directory_path"])
    assert "Files not found" in str(res.data["file.id"])


@pytest.mark.django_db
def test_dataset_files_unknown_project_identifier(client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = {
        "project_identifier": "bleh",
        "storage_service": deep_file_tree["params"]["storage_service"],
        "directories": [{"directory_path": "/dir1/"}],
    }
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        actions,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "project_identifier" in str(res.data)


@pytest.mark.django_db
def test_dataset_files_file_from_wrong_storage_service(client, data_urls, deep_file_tree):
    dataset = factories.DatasetFactory()
    factories.FileStorageFactory(storage_service="test", project_identifier=None)
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        {
            "storage_service": "test",
            "file_actions": [{"id": deep_file_tree["files"]["/dir1/file.csv"].id}],
        },
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Files not found" in res.data["file.id"][0]


@pytest.mark.django_db
def test_dataset_files_missing_project_identifier(client, data_urls):
    dataset = factories.DatasetFactory()
    urls = data_urls(dataset)
    res = client.post(
        urls["file_set"],
        {"storage_service": "ida"},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Field is required" in res.data["project_identifier"]
