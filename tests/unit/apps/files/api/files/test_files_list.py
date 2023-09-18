import pytest

from apps.core import factories


@pytest.fixture
def dataset(file_tree_a):
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(
        dataset=dataset,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/b.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ],
    )
    return dataset


@pytest.mark.django_db
def test_files_get(client, file_tree_a):
    res = client.get(
        "/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    assert res.data["count"] == 16


@pytest.mark.django_db
def test_files_get_no_dataset(client, file_tree_a):
    res = client.get(
        "/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    # no dataset parameter, dataset_metadata should not be included
    assert "dataset_metadata" not in res.data["results"][0]


@pytest.mark.django_db
def test_files_get_dataset_files(client, dataset):
    res = client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()["results"]] == [
        "/dir/a.txt",
        "/dir/b.txt",
        "/dir/c.txt",
    ]


@pytest.mark.django_db
def test_files_get_dataset_files_empty(client, dataset):
    res = client.get(
        "/v3/files",
        {"dataset": dataset.id, "project": "pröject_does_not_exist"},
        content_type="application/json",
    )
    assert res.data["results"] == []


@pytest.mark.django_db
def test_files_get_multiple_storage_projects(client, file_tree_a, file_tree_b):
    res = client.get(
        "/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 16

    res = client.get(
        "/v3/files",
        file_tree_b["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 3

    res = client.get(
        "/v3/files",
        content_type="application/json",
    )
    assert res.json()["count"] == 19


@pytest.mark.django_db
def test_files_list_include_removed(client, file_tree_a):
    file_tree_a["files"]["/dir/c.txt"].delete(soft=True)
    storage_identifier = file_tree_a["files"]["/dir/c.txt"].storage_identifier
    params = {
        **file_tree_a["params"],
        "pagination": False,
        "include_removed": False,
    }
    res = client.get(
        f"/v3/files",
        {**params, "storage_identifier": storage_identifier},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()] == []

    # also non-removed files should be included
    res = client.get(
        f"/v3/files",
        {**params, "storage_identifier": storage_identifier, "include_removed": True},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()] == [
        "/dir/c.txt",
    ]

    # also non-removed files should be included
    res = client.get(
        f"/v3/files",
        {**params, "pathname": "/dir/", "include_removed": True},
        content_type="application/json",
    )
    assert len(res.json()) == 15


@pytest.mark.django_db
def test_files_retrieve_include_removed(client, file_tree_a):
    file_tree_a["files"]["/dir/c.txt"].delete(soft=True)
    file_id = file_tree_a["files"]["/dir/c.txt"].id
    params = {
        **file_tree_a["params"],
        "include_removed": False,
    }
    res = client.get(
        f"/v3/files/{file_id}",
        params,
        content_type="application/json",
    )
    assert res.status_code == 404

    res = client.get(
        f"/v3/files/{file_id}",
        {**params, "include_removed": True},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["pathname"] == "/dir/c.txt"

    # also non-removed files should be included
    file_b_id = file_tree_a["files"]["/dir/b.txt"].id
    res = client.get(
        f"/v3/files/{file_b_id}",
        {**params, "include_removed": True},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["pathname"] == "/dir/b.txt"


@pytest.mark.django_db
def test_files_list_invalid_storage_service(client, file_tree_a):
    res = client.get(
        f"/v3/files?storage_service=doesnotexist",
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "'doesnotexist' is not a valid choice. Valid choices are" in str(
        res.data["storage_service"]
    )
