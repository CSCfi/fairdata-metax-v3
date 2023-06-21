import pytest

from apps.core.models import Dataset
from apps.files.factories import create_project_with_files

pytestmark = [pytest.mark.django_db, pytest.mark.docs]


def test_v1_v3_dataset_v3(client, data_catalog, reference_data, v1_v3_dataset_v3_json):
    res = client.post("/v3/datasets", v1_v3_dataset_v3_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.title == v1_v3_dataset_v3_json["title"]
    assert dataset.language.first().url == v1_v3_dataset_v3_json["language"][0]["url"]
    assert (
        dataset.access_rights.description == v1_v3_dataset_v3_json["access_rights"]["description"]
    )
    assert (
        dataset.field_of_science.first().url == v1_v3_dataset_v3_json["field_of_science"][0]["url"]
    )
    assert dataset.persistent_identifier == v1_v3_dataset_v3_json["persistent_identifier"]


def test_v1_v3_data_catalog_v3(client, v1_v3_data_catalog_v3_json, reference_data):
    res = client.post(
        "/v3/data-catalogs", v1_v3_data_catalog_v3_json, content_type="application/json"
    )
    assert res.status_code == 201


def test_post_file(client, post_file_payload_json):
    res = client.post("/v3/files", post_file_payload_json, content_type="application/json")
    assert res.status_code == 201


def test_minimal_dataset_with_files(
    client, data_catalog, reference_data, minimal_dataset_with_files_json
):
    create_project_with_files(
        storage_service="ida",
        project_identifier="test_project",
        file_paths=["/data/file1.csv", "/data/file2.csv", "/data/file3.csv", "/not-this.txt"],
        file_args={"*": {"byte_size": 1024}},
    )

    res = client.post(
        "/v3/datasets", minimal_dataset_with_files_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert res.json()["data"] == {
        "storage_service": "ida",
        "project_identifier": "test_project",
        "added_files_count": 3,
        "removed_files_count": 0,
        "total_files_count": 3,
        "total_files_byte_size": 3072,
    }
