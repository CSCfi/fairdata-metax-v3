import pytest


@pytest.mark.django_db
def test_directory_storage_project(client, file_tree_a):
    project_identifier = file_tree_a["params"]["project_identifier"]
    file_storage = file_tree_a["params"]["file_storage"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "pagination": False,
            "directory_ordering": "directory_name",
            "project_identifier": project_identifier,
            "file_storage": file_storage,
        },
    )
    assert res.status_code == 200
    assert res.data["directories"][0]["project_identifier"] == project_identifier
    assert res.data["directories"][0]["file_storage"] == file_storage
    assert res.data["files"][0]["project_identifier"] == project_identifier
    assert res.data["files"][0]["file_storage"] == file_storage


@pytest.mark.django_db
def test_directory_storage_project_invalid_project_identifier(client, file_tree_a):
    file_storage = file_tree_a["params"]["file_storage"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "directory_name",
            "project_identifier": "projekti_jota_ei_ole",
            "file_storage": file_storage,
        },
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_directory_storage_project_invalid_file_storage(client, file_tree_a):
    project_identifier = file_tree_a["params"]["project_identifier"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "directory_name",
            "project_identifier": project_identifier,
            "file_storage": "missing_file_storage",
        },
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_directory_storage_project_no_project_identifier(client, file_tree_a):
    file_storage = file_tree_a["params"]["file_storage"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "file_storage": file_storage,
        },
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_directory_storage_project_no_file_storage(client, file_tree_a):
    project_identifier = file_tree_a["params"]["project_identifier"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "directory_name",
            "project_identifier": project_identifier,
        },
    )
    assert res.status_code == 400
