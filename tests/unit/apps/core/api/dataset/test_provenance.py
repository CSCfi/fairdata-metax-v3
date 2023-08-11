import logging

import pytest

from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.provenance]

logger = logging.getLogger(__name__)


@pytest.fixture
def dataset_with_provenance_json(dataset_a_json):
    dataset_a_json["provenance"] = [
        {
            "title": {"fi": "otsikko"},
            "description": {"fi": "kuvaus"},
            "spatial": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
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
                        "code": "20000",
                        "in_scheme": "https://joku.schema.fi",
                    },
                    "person": {"name": "john"},
                }
            ],
        },
        {
            "title": {"en": "second provenance title"},
            "description": {"en": "descriptive description"},
            "spatial": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
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
                        "code": "20000",
                        "in_scheme": "https://joku.schema.fi",
                    },
                    "person": {"name": "john"},
                }
            ],
        }
    ]
    dataset_a_json["actors"] = [{"actor": {"person": {"name": "john"}}, "role": "creator"}]
    return dataset_a_json


@pytest.fixture
def provenance_a_request(client, dataset_with_provenance_json, data_catalog, reference_data):
    return client.post(
        "/v3/datasets", dataset_with_provenance_json, content_type="application/json"
    )


def test_create_dataset_with_provenance(provenance_a_request):
    assert provenance_a_request.status_code == 201
    dataset = Dataset.objects.get(id=provenance_a_request.data["id"])
    actors = dataset.actors.all()
    assert actors.count() == 2
    assert dataset.provenance.count() == 2


def test_edit_provenance(dataset_with_provenance_json, provenance_a_request, client):
    dataset_id = provenance_a_request.data["id"]
    logger.info(f"{provenance_a_request.data=}")
    provenance_json = provenance_a_request.data["provenance"][0]
    provenance_id = provenance_json["id"]
    provenance_json["title"]["fi"] = "new title"
    provenance_json["is_associated_with"].append(
        {
            "person": {"name": "jack"},
        }
    )
    res = client.put(
        f"/v3/datasets/{dataset_id}/provenance/{provenance_id}",
        provenance_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["title"]["fi"] == "new title"
    assert len(res.data["is_associated_with"]) == 2
