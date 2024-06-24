import logging

import pytest
from tests.utils import matchers
from tests.utils.utils import assert_nested_subdict

from apps.core.models import Dataset
from apps.core.models.provenance import Provenance

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
            "roles": ["creator", "publisher"],
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
    assert len(actor.roles) == 2


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
    assert len(set(actor.roles)) == 2


def test_preservation_event(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["provenance"] = [
        {
            "description": {"fi": "kuvaus"},
            "preservation_event": {
                "url": "http://uri.suomi.fi/codelist/fairdata/preservation_event/code/cre",
            },
        }
    ]

    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    assert res1.data["provenance"][0]["preservation_event"]["pref_label"]["en"] == "Creation"


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


def test_replace_existing_provenances(
    admin_client, dataset_with_provenance_json, data_catalog, reference_data, mocker
):
    dataset = {**dataset_with_provenance_json}
    resp = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert resp.status_code == 201

    dataset_id = resp.json()["id"]
    provenances = [
        {
            "title": {"fi": "uusi otsikko"},
            "description": {"fi": "uusi kuvaus"},
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
            "used_entity": [
                {
                    "title": {"en": "New entity"},
                    "description": {"en": "This a new entity"},
                    "entity_identifier": "https://example.com/some_sound",
                    "type": {
                        "url": "http://uri.suomi.fi/codelist/fairdata/resource_type/code/sound"
                    },
                }
            ],
        },
        {"title": {"en": "simple provenance"}},
    ]

    create = mocker.spy(Provenance.objects, "create")
    bulk_create = mocker.spy(Provenance.objects, "bulk_create")

    resp = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"provenance": provenances}, content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert_nested_subdict(
        provenances,
        data["provenance"],
    )

    assert Provenance.all_objects.count() == 4
    assert create.call_count == 0
    assert bulk_create.call_count == 1
