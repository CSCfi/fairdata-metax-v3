import pytest


@pytest.mark.django_db
def test_directory_file_storage(client, file_tree_a):
    project_identifier = file_tree_a["params"]["project_identifier"]
    storage_service = file_tree_a["params"]["storage_service"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "pagination": False,
            "directory_ordering": "directory_name",
            "project_identifier": project_identifier,
            "storage_service": storage_service,
        },
    )
    assert res.status_code == 200
    assert res.data["directories"][0]["project_identifier"] == project_identifier
    assert res.data["directories"][0]["storage_service"] == storage_service
    assert res.data["files"][0]["project_identifier"] == project_identifier
    assert res.data["files"][0]["storage_service"] == storage_service


@pytest.mark.django_db
def test_directory_file_storage_invalid_project_identifier(client, file_tree_a):
    storage_service = file_tree_a["params"]["storage_service"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "directory_name",
            "project_identifier": "projekti_jota_ei_ole",
            "storage_service": storage_service,
        },
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_directory_file_storage_invalid_file_storage(client, file_tree_a):
    project_identifier = file_tree_a["params"]["project_identifier"]
    res = client.get(
        "/v3/directories",
        {
            "path": "/",
            "directory_ordering": "directory_name",
            "project_identifier": project_identifier,
            "storage_service": "invalid",
        },
    )
    assert res.status_code == 400
    assert "not a valid choice" in res.json()["storage_service"][0]


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_directory_file_storage_no_file_storage(client, file_tree_a):
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
