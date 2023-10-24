import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.file]


def test_directory_file_storage(client, file_tree_a):
    project = file_tree_a["params"]["project"]
    storage_service = file_tree_a["params"]["storage_service"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "pagination": False,
            "directory_ordering": "name",
            "project": project,
            "storage_service": storage_service,
        },
    )
    assert res.status_code == 200
    assert res.data["directories"][0]["project"] == project
    assert res.data["directories"][0]["storage_service"] == storage_service
    assert res.data["files"][0]["project"] == project
    assert res.data["files"][0]["storage_service"] == storage_service


def test_directory_file_storage_invalid_project_identifier(client, file_tree_a):
    storage_service = file_tree_a["params"]["storage_service"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "name",
            "project": "projekti_jota_ei_ole",
            "storage_service": storage_service,
        },
    )
    assert res.status_code == 404


def test_directory_file_storage_invalid_file_storage(client, file_tree_a):
    project = file_tree_a["params"]["project"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "name",
            "project": project,
            "storage_service": "invalid",
        },
    )
    assert res.status_code == 400
    assert "not a valid choice" in res.json()["storage_service"][0]


def test_directory_file_storage_no_project_identifier(client, file_tree_a):
    storage_service = file_tree_a["params"]["storage_service"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "storage_service": storage_service,
        },
    )
    assert res.status_code == 400


def test_directory_file_storage_no_file_storage(client, file_tree_a):
    project = file_tree_a["params"]["project"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "name",
            "project": project,
        },
    )
    assert res.status_code == 400
