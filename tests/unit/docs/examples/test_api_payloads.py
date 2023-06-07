import pytest

from apps.core.models import Dataset

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
