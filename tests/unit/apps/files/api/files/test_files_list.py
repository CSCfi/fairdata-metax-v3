import pytest

from apps.core import factories


@pytest.fixture
def dataset(file_tree_a):
    dataset = factories.DatasetFactory()
    dataset.files.set(
        [
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/b.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ]
    )
    return dataset


@pytest.mark.django_db
def test_files_get(client, file_tree_a):
    res = client.get(
        "/rest/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 16


@pytest.mark.django_db
def test_files_get_dataset_files(client, dataset):
    res = client.get(
        "/rest/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert [f["file_path"] for f in res.json()["results"]] == [
        "/dir/a.txt",
        "/dir/b.txt",
        "/dir/c.txt",
    ]


@pytest.mark.django_db
def test_files_get_dataset_files(client, dataset):
    res = client.get(
        "/rest/v3/files",
        {"dataset": dataset.id, "project_identifier": "pröject_does_not_exist"},
        content_type="application/json",
    )
    assert res.data["results"] == []


@pytest.mark.django_db
def test_files_get_multiple_storage_projects(client, file_tree_a, file_tree_b):
    res = client.get(
        "/rest/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 16

    res = client.get(
        "/rest/v3/files",
        file_tree_b["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 3

    res = client.get(
        "/rest/v3/files",
        content_type="application/json",
    )
    assert res.json()["count"] == 19
