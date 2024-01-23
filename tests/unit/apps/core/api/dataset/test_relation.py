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

    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    assert str(res1.data["other_identifiers"][0]["metax_ids"][0]) == dataset_with_urn.data["id"]
    assert str(res1.data["relation"][0]["metax_ids"][0]) == dataset_with_doi.data["id"]
