import logging

import pytest
from tests.utils import matchers

from apps.core.models import Dataset

print("MATCHERS", matchers.DictContaining)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.provenance]

logger = logging.getLogger(__name__)


@pytest.fixture
def dataset_with_provenance_json(dataset_a_json, entity_json):
    dataset_a_json["provenance"] = [
        {
            "title": {"fi": "otsikko"},
            "description": {"fi": "kuvaus"},
            "spatial": {"reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"}},
            "lifecycle_event": {
                "url": "http://uri.suomi.fi/codelist/fairdata/lifecycle_event/code/planned",
            },
            "event_outcome": {
                "url": "http://uri.suomi.fi/codelist/fairdata/event_outcome/code/success"
            },
            "is_associated_with": [
                {
                    "organization": {
                        "pref_label": {"fi": "CSC"},
                    },
                    "person": {"name": "john"},
                }
            ],
            "used_entity": [entity_json],
        },
        {
            "title": {"en": "second provenance title"},
            "description": {"en": "descriptive description"},
            "spatial": {"reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"}},
            "lifecycle_event": {
                "url": "http://uri.suomi.fi/codelist/fairdata/lifecycle_event/code/planned",
            },
            "event_outcome": {
                "url": "http://uri.suomi.fi/codelist/fairdata/event_outcome/code/success"
            },
            "is_associated_with": [
                {
                    "organization": {
                        "pref_label": {"fi": "CSC"},
                    },
                    "person": {"name": "john"},
                }
            ],
        },
    ]
    dataset_a_json["actors"] = [
        {
            "person": {"name": "john"},
            "organization": {
                "pref_label": {"fi": "CSC"},
            },
            "roles": ["creator"],
        }
    ]
    return dataset_a_json


@pytest.fixture
def provenance_a_request(admin_client, dataset_with_provenance_json, data_catalog, reference_data):
    return admin_client.post(
        "/v3/datasets", dataset_with_provenance_json, content_type="application/json"
    )


def test_create_dataset_with_provenance(provenance_a_request, entity_json):
    assert provenance_a_request.status_code == 201

    assert provenance_a_request.data["provenance"][0]["used_entity"] == [
        {**entity_json, "type": matchers.DictContaining(entity_json["type"])}
    ]
    dataset = Dataset.objects.get(id=provenance_a_request.data["id"])
    actors = dataset.actors.all()
    assert actors.count() == 1
    assert dataset.provenance.count() == 2
    actor = actors.first()
    assert len(set(actor.roles)) == 1


def test_update_dataset_with_provenance(
    admin_client, dataset_with_provenance_json, data_catalog, reference_data
):
    dataset = {**dataset_with_provenance_json}
    provenance = dataset.pop("provenance")
    resp = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert resp.data.get("provenance") == []

    # add provenance to dataset that didn't have it before
    dataset_id = resp.data["id"]
    resp = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"provenance": provenance}, content_type="application/json"
    )
    assert resp.status_code == 200
    dataset = Dataset.objects.get(id=resp.data["id"])
    actors = dataset.actors.all()
    assert actors.count() == 1
    assert dataset.provenance.count() == 2
    actor = actors.first()
    assert len(set(actor.roles)) == 1


def test_edit_provenance(dataset_with_provenance_json, provenance_a_request, admin_client):
    dataset_id = provenance_a_request.data["id"]
    logger.info(f"{provenance_a_request.data=}")
    provenance_json = provenance_a_request.data["provenance"][0]
    provenance_id = provenance_json["id"]
    provenance_json["title"]["fi"] = "new title"
    assert len(provenance_a_request.data["provenance"][0]["is_associated_with"]) == 1
    provenance_json["is_associated_with"].append(
        {
            "person": {"name": "jack"},
        }
    )
    res = admin_client.put(
        f"/v3/datasets/{dataset_id}/provenance/{provenance_id}",
        provenance_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["title"]["fi"] == "new title"
    assert len(res.data["is_associated_with"]) == 2


def test_provenance_new_version(dataset_with_provenance_json, provenance_a_request, admin_client):
    dataset_id = provenance_a_request.data["id"]
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/new-version",
        content_type="application/json",
    )
    new_id = res.data["id"]
    assert res.status_code == 201

    original = Dataset.objects.get(id=dataset_id)
    new = Dataset.objects.get(id=new_id)
    assert new.provenance.first().id != original.provenance.first().id
    assert (
        new.provenance.first().is_associated_with.first().person.name
        == original.provenance.first().is_associated_with.first().person.name
    )
    assert (
        new.provenance.first().is_associated_with.first().id
        != original.provenance.first().is_associated_with.first().id
    )

    assert new.provenance.first().is_associated_with.first().id == new.actors.first().id
