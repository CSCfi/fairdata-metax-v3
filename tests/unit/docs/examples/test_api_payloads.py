import pytest

from apps.core.models import Dataset
from apps.files.factories import create_project_with_files

from .conftest import load_test_json

pytestmark = [pytest.mark.django_db, pytest.mark.docs]


def test_v1_v3_dataset_v3(
    admin_client, data_catalog, reference_data, v1_v3_dataset_v3_json, harvested_datacatalog
):
    v1_v3_dataset_v3_json["data_catalog"] = harvested_datacatalog["id"]
    res = admin_client.post("/v3/datasets", v1_v3_dataset_v3_json, content_type="application/json")
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


def test_v1_v3_data_catalog_v3(admin_client, v1_v3_data_catalog_v3_json, reference_data):
    res = admin_client.post(
        "/v3/data-catalogs", v1_v3_data_catalog_v3_json, content_type="application/json"
    )
    assert res.status_code == 201


def test_post_file(admin_client, post_file_payload_json):
    res = admin_client.post("/v3/files", post_file_payload_json, content_type="application/json")
    assert res.status_code == 201


def test_minimal_dataset_with_files(
    admin_client, data_catalog, reference_data, minimal_dataset_with_files_json
):
    create_project_with_files(
        storage_service="ida",
        csc_project="test_project",
        file_paths=["/data/file1.csv", "/data/file2.csv", "/data/file3.csv", "/not-this.txt"],
        file_args={"*": {"size": 1024}},
    )

    res = admin_client.post(
        "/v3/datasets", minimal_dataset_with_files_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert res.json()["fileset"] == {
        "storage_service": "ida",
        "csc_project": "test_project",
        "added_files_count": 3,
        "removed_files_count": 0,
        "total_files_count": 3,
        "total_files_size": 3072,
    }


def test_convert_from_legacy_payload(admin_client, data_catalog):
    payload = load_test_json("convert_from_legacy_payload.json")
    res = admin_client.post(
        "/v3/datasets/convert_from_legacy", payload, content_type="application/json"
    )
    expected_data = load_test_json("convert_from_legacy_response.json")
    assert res.status_code == 200
    assert res.json() == expected_data
