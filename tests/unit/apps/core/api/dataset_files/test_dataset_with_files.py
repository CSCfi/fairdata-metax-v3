"""Tests for viewing and updating dataset files with files parameter of /dataset and /dataset/<id> endpoints."""

import pytest
from tests.utils import assert_nested_subdict

from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def dataset_json_with_files(deep_file_tree, data_catalog):
    return {
        "data_catalog": data_catalog.id,
        "title": {"en": "Test dataset"},
        "fileset": {
            **deep_file_tree["params"],
            "directory_actions": [
                {
                    "pathname": "/dir1/",
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
def dataset_json_with_files_published(dataset_json_with_files, deep_file_tree, data_catalog, reference_data):
    return {
        **dataset_json_with_files,
        "state": "published",
        "pid_type": "URN",
        "access_rights": {
            "access_type": {
                "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
            },
            "license": [
                {
                    "url": "http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0"
                }
            ]
        },
        "actors": [
            {
                "organization": {
                    "pref_label": {
                        "en": "test org"
                    }
                },
                "roles": [
                    "creator",
                    "publisher"
                ]
            }
        ],
    }


@pytest.fixture
def dataset_json_with_no_files(deep_file_tree, data_catalog):
    return {
        "data_catalog": data_catalog.id,
        "title": {"en": "Test dataset"},
    }


def test_dataset_post_dataset_with_files(
    admin_client, deep_file_tree, dataset_json_with_files, data_urls
):
    res = admin_client.post(
        f"/v3/datasets",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert res.data["fileset"]["added_files_count"] == 3
    assert res.data["fileset"]["removed_files_count"] == 0
    assert res.data["fileset"]["total_files_count"] == 3

    url = data_urls(res.data["id"])["directories"]
    res = admin_client.get(url, {"pagination": "false"})
    assert_nested_subdict(
        {
            "directories": [
                {"pathname": "/dir1/", "dataset_metadata": {"title": "directory"}},
            ],
            "files": [{"pathname": "/rootfile.txt", "dataset_metadata": {"title": "file"}}],
        },
        res.json(),
    )


def test_dataset_post_dataset_with_files_new_version(
    admin_client, deep_file_tree, dataset_json_with_files_published, data_urls, reference_data
):
    res = admin_client.post(
        f"/v3/datasets",
        dataset_json_with_files_published,
        content_type="application/json",
    )
    original_id = res.data["id"]
    assert res.status_code == 201

    # Create new version of dataset with files
    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/new-version"
    )
    new_id = res.data["id"]
    assert new_id != original_id

    url = data_urls(new_id)["directories"]
    res = admin_client.get(url, {"pagination": "false"})
    assert_nested_subdict(
        {
            "directories": [
                {"pathname": "/dir1/", "dataset_metadata": {"title": "directory"}},
            ],
            "files": [{"pathname": "/rootfile.txt", "dataset_metadata": {"title": "file"}}],
        },
        res.json(),
    )

    # Check that versions have separate but identical file sets
    original = Dataset.objects.get(id=original_id)
    new = Dataset.objects.get(id=new_id)
    assert new.file_set.id != original.file_set.id
    assert set(new.file_set.files.all()) == set(
        original.file_set.files.all()
    )  # files should be the same
    assert new.file_set.file_metadata.count() == original.file_set.file_metadata.count()
    assert new.file_set.file_metadata.first().id != original.file_set.file_metadata.first().id
    assert (
        new.file_set.file_metadata.first().title == original.file_set.file_metadata.first().title
    )
    assert new.file_set.directory_metadata.count() == original.file_set.directory_metadata.count()
    assert (
        new.file_set.directory_metadata.first().id
        != original.file_set.directory_metadata.first().id
    )
    assert (
        new.file_set.directory_metadata.first().title
        == original.file_set.directory_metadata.first().title
    )


def test_dataset_get_dataset_with_files(admin_client, deep_file_tree, dataset_json_with_files):
    res = admin_client.post(
        f"/v3/datasets",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = admin_client.get(f"/v3/datasets/{res.data['id']}")
    assert res.status_code == 200
    assert res.data["fileset"] == {
        # no added_files_count or removed_files_count should be present for GET
        "storage_service": deep_file_tree["params"]["storage_service"],
        "csc_project": deep_file_tree["params"]["csc_project"],
        "total_files_count": 3,
        "total_files_size": 3 * 1024,
    }


def test_dataset_get_dataset_with_no_files(
    admin_client, deep_file_tree, dataset_json_with_no_files
):
    res = admin_client.post(
        f"/v3/datasets",
        dataset_json_with_no_files,
        content_type="application/json",
    )
    assert res.status_code == 201

    res = admin_client.get(f"/v3/datasets/{res.data['id']}")
    assert res.status_code == 200
    assert "files" not in res.data  # no files dict should be present if dataset has no files


def test_dataset_modify_dataset_with_files(
    admin_client, deep_file_tree, dataset_json_with_files, data_urls
):
    res = admin_client.post(
        f"/v3/datasets",
        dataset_json_with_files,
        content_type="application/json",
    )
    assert res.status_code == 201

    actions = {
        **deep_file_tree["params"],
        "directory_actions": [{"pathname": "/dir1/", "action": "remove"}],
        "file_actions": [{"id": deep_file_tree["files"]["/dir3/sub1/file.txt"].id}],
    }

    dataset_json = {k: v for k, v in res.data.items() if v != None}

    dataset_id = res.data["id"]
    urls = data_urls(dataset_id)
    res = admin_client.put(
        urls["dataset"],
        {**dataset_json, "fileset": actions},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["fileset"]["added_files_count"] == 1
    assert res.data["fileset"]["removed_files_count"] == 2
    assert res.data["fileset"]["total_files_count"] == 2

    res = admin_client.get(urls["directories"], {"pagination": "false"})
    assert_nested_subdict(
        {
            "directories": [
                {"pathname": "/dir3/"},
            ],
            "files": [{"pathname": "/rootfile.txt", "dataset_metadata": {"title": "file"}}],
        },
        res.json(),
    )
