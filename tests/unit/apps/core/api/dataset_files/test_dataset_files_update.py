"""Tests for updating dataset files with /dataset/<id>/files endpoint."""

from typing import Dict

import pytest
from tests.utils import assert_nested_subdict

from apps.core import factories

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_dataset_files_post_empty(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "file_actions": [],
        "directory_actions": [],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    fileset = res.data["fileset"]
    assert fileset["added_files_count"] == 0
    assert fileset["removed_files_count"] == 0
    assert fileset["total_files_count"] == 0
    assert fileset["total_files_size"] == 0
    assert fileset["project"] == deep_file_tree["params"]["project"]

    res = admin_client.get(urls["files"])
    assert res.status_code == 200
    assert res.json()["count"] == 0

    res = admin_client.get(urls["directories"])
    assert res.status_code == 200
    assert res.json()["count"] == 0


def test_dataset_files_post_multiple_file_sets(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = deep_file_tree["params"]
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Cannot alter storage for existing FileSet
    factories.FileStorageFactory(storage_service="test", project=None)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": {"storage_service": "test"}},
        content_type="application/json",
    )

    assert res.status_code == 400
    assert res.json() == {
        "project": "Wrong project for fileset.",
        "storage_service": "Wrong storage_service for fileset.",
    }


def test_dataset_patch_fileset(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"pathname": "/dir2/"},
            {
                "pathname": "/dir2/subdir2/",
                "action": "remove",
            },
            {"pathname": "/dir2/subdir2/subsub/"},
            {
                "pathname": "/dir2/subdir2/subsub/subsubsub2/",
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    fileset = res.data["fileset"]
    assert fileset["added_files_count"] == 6
    assert fileset["removed_files_count"] == 0
    assert fileset["total_files_count"] == 6

    res = admin_client.get(urls["files"])
    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/rootfile.txt"},
                {"pathname": "/dir1/sub/file.csv"},
                {"pathname": "/dir2/a.txt"},
                {"pathname": "/dir2/subdir1/file1.txt"},
                {"pathname": "/dir2/subdir1/file3.txt"},
                {"pathname": "/dir2/subdir2/subsub/subsubsub1/file.txt"},
            ]
        },
        res.json(),
    )


def test_dataset_files_post_noop_add(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        storage=deep_file_tree["storage"],
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    fileset = res.data["fileset"]
    assert res.status_code == 200
    assert fileset["added_files_count"] == 0
    assert fileset["removed_files_count"] == 0
    assert fileset["total_files_count"] == len(deep_file_tree["files"])


def test_dataset_files_post_noop_remove(admin_client, deep_file_tree, data_urls):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    fileset = res.data["fileset"]
    assert res.status_code == 200
    assert fileset["added_files_count"] == 0
    assert fileset["removed_files_count"] == 0
    assert fileset["total_files_count"] == 0


@pytest.fixture
def dataset_with_metadata(admin_client, deep_file_tree, data_urls) -> Dict:
    dataset = factories.DatasetFactory()
    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"pathname": "/dir2/subdir1/", "dataset_metadata": {"title": "directory title"}},
        ],
        "file_actions": [
            {
                "id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id,
                "action": "update",
                "dataset_metadata": {"title": "file title"},
            },
        ],
    }

    url = data_urls(dataset)["dataset"]
    res = admin_client.patch(
        url,
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    return dataset


def test_dataset_files_post_metadata_get_files(admin_client, dataset_with_metadata, data_urls):
    url = data_urls(dataset_with_metadata)["files"]
    res = admin_client.get(url)
    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/dir2/subdir1/file1.txt"},
                {
                    "pathname": "/dir2/subdir1/file2.txt",
                    "dataset_metadata": {"title": "file title"},
                },
                {"pathname": "/dir2/subdir1/file3.txt"},
            ],
        },
        res.json(),
    )


def test_dataset_files_post_metadata_get_directories(
    admin_client, dataset_with_metadata, data_urls
):
    url = data_urls(dataset_with_metadata)["directories"]
    res = admin_client.get(url, {"path": "/dir2/subdir1", "pagination": "false"})
    assert_nested_subdict(
        {
            "directory": {
                "name": "subdir1",
                "dataset_metadata": {"title": "directory title"},
            },
            "files": [
                {"pathname": "/dir2/subdir1/file1.txt"},
                {
                    "pathname": "/dir2/subdir1/file2.txt",
                    "dataset_metadata": {"title": "file title"},
                },
                {"pathname": "/dir2/subdir1/file3.txt"},
            ],
        },
        res.json(),
    )


def test_dataset_files_post_multiple_metadata_updates(admin_client, deep_file_tree, data_urls):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    res = admin_client.get(urls["files"])

    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/rootfile.txt", "dataset_metadata": {"title": "title 2"}},
            ]
        },
        res.json(),
    )


def test_dataset_files_post_update_for_existing_metadata(admin_client, deep_file_tree, data_urls):
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
                "pathname": "/",
                "dataset_metadata": {"title": "root dir"},
            },
        ],
    }
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
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
                "pathname": "/",
                "dataset_metadata": {"title": "root dir updated"},
            },
        ],
    }
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.get(urls["files"])
    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/rootfile.txt", "dataset_metadata": {"title": "title 2"}},
            ]
        },
        res.json(),
    )

    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert res.data["directory"]["dataset_metadata"]["title"] == "root dir updated"


def test_dataset_files_post_remove_file_metadata(admin_client, deep_file_tree, data_urls):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = admin_client.get(urls["files"])
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    fileset = res.data["fileset"]
    assert res.status_code == 200

    res = admin_client.get(urls["files"])
    assert res.data["results"][0]["dataset_metadata"] is None


def test_dataset_files_post_none_file_metadata(admin_client, deep_file_tree, data_urls):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    fileset = res.data["fileset"]
    assert res.status_code == 200

    res = admin_client.get(urls["files"])
    assert res.data["results"][0]["dataset_metadata"] is None


def test_dataset_files_post_remove_directory_metadata(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "pathname": "/dir1/",
                "dataset_metadata": {"title": "title"},
            },
        ],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    # check metadata is present
    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert "dataset_metadata" in res.data["directories"][0]

    # remove metadata by setting it to None
    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "pathname": "/dir1/",
                "action": "update",
                "dataset_metadata": None,
            },
        ],
    }
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert res.data["directories"][0]["dataset_metadata"] is None


def test_dataset_files_post_none_directory_metadata(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {
                "pathname": "/dir1/",
                "dataset_metadata": None,
            },
        ],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert res.data["directories"][0]["dataset_metadata"] is None


def test_dataset_files_multiple_post_requests(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"pathname": "/dir3/"},
            {"pathname": "/dir2/"},
        ],
        "file_actions": [
            {"id": deep_file_tree["files"]["/dir1/file.csv"].id},
        ],
    }

    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    fileset = res.data["fileset"]
    assert fileset["added_files_count"] == 13
    assert fileset["removed_files_count"] == 0
    assert fileset["total_files_count"] == 13

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [
            {"pathname": "/dir1/sub/"},
            {"pathname": "/dir3/", "action": "remove"},
        ],
        "file_actions": [
            {"id": deep_file_tree["files"]["/dir2/subdir1/file1.txt"].id, "action": "remove"},
            {"id": deep_file_tree["files"]["/dir2/subdir1/file2.txt"].id, "action": "remove"},
        ],
    }
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    fileset = res.data["fileset"]
    assert fileset["added_files_count"] == 1
    assert fileset["removed_files_count"] == 4
    assert fileset["total_files_count"] == 10
    res = admin_client.get(urls["files"])

    assert_nested_subdict(
        {
            "results": [
                {"pathname": "/dir1/file.csv"},
                {"pathname": "/dir1/sub/file.csv"},
                {"pathname": "/dir2/a.txt"},
                {"pathname": "/dir2/subdir1/file3.txt"},
                {"pathname": "/dir2/subdir2/file1.txt"},
                {"pathname": "/dir2/subdir2/file2.txt"},
                {"pathname": "/dir2/subdir2/file3.txt"},
                {"pathname": "/dir2/subdir2/subsub/subsubsub1/file.txt"},
                {"pathname": "/dir2/subdir2/subsub/subsubsub2/file1.txt"},
                {"pathname": "/dir2/subdir2/subsub/subsubsub2/file2.txt"},
            ]
        },
        res.json(),
    )


def test_dataset_files_all_metadata_fields(
    admin_client, deep_file_tree, reference_data, data_urls
):
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
        "directory_actions": [{"pathname": "/dir1/", "dataset_metadata": directory_metadata}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert_nested_subdict(
        {
            "directories": [
                {"pathname": "/dir1/", "dataset_metadata": directory_metadata},
            ],
            "files": [{"pathname": "/rootfile.txt", "dataset_metadata": file_metadata}],
        },
        res.json(),
    )


def test_dataset_files_invalid_file_type(admin_client, deep_file_tree, reference_data, data_urls):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Invalid values" in res.data["fileset"]["file_type"]


def test_dataset_files_invalid_use_category(
    admin_client, deep_file_tree, reference_data, data_urls
):
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
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Invalid values" in res.data["fileset"]["use_category"]


def test_dataset_files_wrong_project_identifier(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    other_storage = factories.FileStorageFactory(
        storage_service=deep_file_tree["storage"].storage_service
    )
    actions = {
        "project": other_storage.project,
        "storage_service": other_storage.storage_service,
        "directory_actions": [{"pathname": "/dir1/"}],
        "file_actions": [{"id": deep_file_tree["files"]["/rootfile.txt"].id}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Directory not found" in str(res.data["fileset"]["pathname"])
    assert "Files not found" in str(res.data["fileset"]["file.id"])


def test_dataset_files_unknown_project_identifier(admin_client, deep_file_tree, data_urls):
    dataset = factories.DatasetFactory()
    actions = {
        "project": "bleh",
        "storage_service": deep_file_tree["params"]["storage_service"],
        "directory_actions": [{"pathname": "/dir1/"}],
    }
    urls = data_urls(dataset)
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "project" in str(res.data["fileset"])


def test_dataset_files_file_from_wrong_storage_service(admin_client, data_urls, deep_file_tree):
    dataset = factories.DatasetFactory()
    factories.FileStorageFactory(storage_service="test", project=None)
    urls = data_urls(dataset)
    actions = {
        "storage_service": "test",
        "file_actions": [{"id": deep_file_tree["files"]["/dir1/file.csv"].id}],
    }
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Files not found" in res.data["fileset"]["file.id"][0]


def test_dataset_files_missing_project_identifier(admin_client, data_urls):
    dataset = factories.DatasetFactory()
    urls = data_urls(dataset)
    actions = {"storage_service": "ida"}
    res = admin_client.patch(
        urls["dataset"],
        {"fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Field is required" in res.data["fileset"]["project"]
