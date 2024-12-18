import logging

import pytest
from tests.utils import assert_nested_subdict

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_entity_relation(admin_client, dataset_a_json, entity_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    relation = {
        "entity": entity_json,
        "relation_type": {"url": "http://purl.org/dc/terms/relation"},
    }
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"relation": [relation]},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict([relation], res.data["relation"])


def test_entity_relation_found_in_metax(
    admin_client, dataset_a_json, entity_json, data_catalog, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    entity_json["entity_identifier"] = res1.data["persistent_identifier"]
    relation = {
        "entity": entity_json,
        "relation_type": {"url": "http://purl.org/dc/terms/relation"},
    }
    dataset_a_json["relation"] = [relation]

    res2 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")

    assert res2.status_code == 201
    assert_nested_subdict([relation], res2.data["relation"])
    existing_metax_id = str(res2.data["relation"][0]["metax_ids"][0])
    assert existing_metax_id == res1.data["id"]


def test_other_identifier_found_in_metax(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    other_identifier = {"notation": res1.data["persistent_identifier"]}

    dataset_a_json["other_identifiers"] = [other_identifier]

    res2 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res2.status_code == 201
    assert str(res2.data["other_identifiers"][0]["metax_ids"][0]) == res1.data["id"]


def test_other_identifier_found_in_metax_ignore_draft(
    admin_client, dataset_a_json, data_catalog, data_catalog_harvested, reference_data
):
    dataset_1_json = {
        **dataset_a_json,
        "state": "draft",
        "persistent_identifier": "i have a pid",
        "generate_pid_on_publish": None,
        "data_catalog": data_catalog_harvested.id,
    }

    res1 = admin_client.post("/v3/datasets", dataset_1_json, content_type="application/json")
    assert res1.status_code == 201

    # Dataset 1 is a draft, it should be ignored when determining metax_ids
    other_identifier = {"notation": res1.data["persistent_identifier"]}
    dataset_a_json["other_identifiers"] = [other_identifier]

    res2 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res2.status_code == 201
    assert res2.data["other_identifiers"][0]["metax_ids"] == []


def test_other_identifier_found_in_metax_list(
    admin_client,
    dataset_a_json,
    data_catalog,
    data_catalog_harvested_b,
    data_catalog_harvested,
    reference_data,
):
    """Test multiple datasets with same pid."""
    # Create 2 datasets with same pid
    first_dataset = {
        **dataset_a_json,
        "data_catalog": data_catalog_harvested_b.id,
        "persistent_identifier": "same pid",
        "generate_pid_on_publish": None,
    }

    res1 = admin_client.post("/v3/datasets", first_dataset, content_type="application/json")
    assert res1.status_code == 201

    other_dataset = {
        **dataset_a_json,
        "data_catalog": data_catalog_harvested.id,
        "persistent_identifier": res1.data["persistent_identifier"],
        "generate_pid_on_publish": None,
    }
    res2 = admin_client.post("/v3/datasets", other_dataset, content_type="application/json")
    assert res2.status_code == 201

    # Create dataset with other_identifier
    other_identifier = {"notation": res1.data["persistent_identifier"]}
    dataset_a_json["other_identifiers"] = [other_identifier]

    res3 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res3.status_code == 201

    # Dataset should have both previous metax_ids in other_identifier
    assert set(res3.json()["other_identifiers"][0]["metax_ids"]) == {
        res1.data["id"],
        res2.data["id"],
    }

    # Test that dataset has same other_identifiers when dataset list is requested
    res4 = admin_client.get("/v3/datasets", content_type="application/json")
    assert res4.status_code == 200
    other_identifier_datasets = [
        item for item in res4.json()["results"] if item["id"] == res3.data["id"]
    ]
    assert len(other_identifier_datasets) == 1
    assert set(other_identifier_datasets[0]["other_identifiers"][0]["metax_ids"]) == {
        res1.data["id"],
        res2.data["id"],
    }


def test_relation_pids_given_as_urls(
    admin_client,
    dataset_a_json,
    entity_json,
    data_catalog,
    datacatalog_harvested_json,
    reference_data,
):
    dataset_with_urn = admin_client.post(
        "/v3/datasets", dataset_a_json, content_type="application/json"
    )
    assert dataset_with_urn.status_code == 201

    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "doi:test_doi"
    dataset_a_json["generate_pid_on_publish"] = None

    dataset_with_doi = admin_client.post(
        "/v3/datasets", dataset_a_json, content_type="application/json"
    )

    other_identifier = {
        "notation": "http://urn.fi/" + dataset_with_urn.data["persistent_identifier"]
    }

    entity_json["entity_identifier"] = "https://doi.org/" + "test_doi"
    relation = {
        "entity": entity_json,
        "relation_type": {"url": "http://purl.org/dc/terms/relation"},
    }

    dataset_a_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-ida"
    del dataset_a_json["persistent_identifier"]
    dataset_a_json["relation"] = [relation]
    dataset_a_json["other_identifiers"] = [other_identifier]
    dataset_a_json["generate_pid_on_publish"] = "URN"

    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    assert str(res1.data["other_identifiers"][0]["metax_ids"][0]) == dataset_with_urn.data["id"]
    assert str(res1.data["relation"][0]["metax_ids"][0]) == dataset_with_doi.data["id"]
