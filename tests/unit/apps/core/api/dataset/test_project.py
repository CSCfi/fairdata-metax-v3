import logging

import pytest
from tests.utils import matchers
from tests.utils.utils import assert_nested_subdict

from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.project]

logger = logging.getLogger(__name__)


@pytest.fixture
def dataset_with_project_json(dataset_a_json, entity_json):
    dataset_a_json["projects"] = [
        {
            "id": "ac661477-8ff2-45a5-8e65-57578f20201e",
            "title": {"en": "project", "fi": "projekti"},
            "project_identifier": "project_identifier",
            "participating_organizations": [
                {
                    "url": "http://uri.suomi.fi/codelist/fairdata/organization/code/10076",
                }
            ],
            "funding": [
                {
                    "funder": {
                        "funder_type": {
                            "url": "http://uri.suomi.fi/codelist/fairdata/funder_type/code/other-public",
                        },
                        "organization": {
                            "url": "http://uri.suomi.fi/codelist/fairdata/organization/code/10076"
                        },
                    },
                    "funding_identifier": "funding identifier",
                }
            ],
        }
    ]
    return dataset_a_json


@pytest.fixture
def project_a_request(admin_client, dataset_with_project_json, data_catalog, reference_data):
    return admin_client.post(
        "/v3/datasets", dataset_with_project_json, content_type="application/json"
    )


def test_create_dataset_with_project(project_a_request, entity_json):
    print(project_a_request.data)
    assert project_a_request.status_code == 201

    dataset = Dataset.objects.get(id=project_a_request.data["id"])
    projects = dataset.projects.all()
    assert projects.count() == 1


def test_update_project_with_funder(
    admin_client, dataset_with_project_json, data_catalog, reference_data
):
    dataset = {**dataset_with_project_json}
    projects = dataset.pop("projects")
    resp = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert resp.data.get("projects") == []

    dataset_id = resp.data["id"]
    resp = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"projects": projects}, content_type="application/json"
    )
    assert resp.status_code == 200
    dataset = Dataset.objects.get(id=resp.data["id"])
    projects = dataset.projects.all()
    assert projects.count() == 1
    assert dataset.projects.count() == 1


def test_update_project_with_empty_funder(
    admin_client, dataset_with_project_json, data_catalog, reference_data
):
    dataset = {**dataset_with_project_json}
    projects = dataset.pop("projects")
    resp = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert resp.data.get("projects") == []

    projects[0]["funding"][0]["funder"] = {}
    dataset_id = resp.data["id"]
    resp = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"projects": projects}, content_type="application/json"
    )
    assert resp.status_code == 400
    assert (
        resp.data["projects"][0]["funding"][0]["funder"]["non_field_errors"][0]
        == "At least one of fields 'funder_type', 'organization' is required."
    )
