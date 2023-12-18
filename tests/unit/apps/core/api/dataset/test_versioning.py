import logging

import pytest

from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.versioning]

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "query_param",
    ["latest_published=true", "published_revision=1", "all_published_revisions=true"],
)
def test_dataset_revisions_latest_published(
    admin_client, dataset_a, data_catalog, reference_data, query_param
):
    assert dataset_a.response.status_code == 201

    res1 = admin_client.get(
        f"/v3/datasets/{dataset_a.response.data['id']}/revisions?{query_param}",
        content_type="application/json",
    )
    assert res1.status_code == 200
    if not isinstance(res1.data, list):
        res1.data = [res1.data]
    for row in res1.data:
        for field, value in row.items():
            if field not in ["created", "modified"]:
                assert value == dataset_a.response.data[field]


def test_dataset_versions(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    dataset1 = Dataset.objects.get(id=res1.data["id"])

    res2 = admin_client.post(
        f"/v3/datasets/{res1.data['id']}/new-version", content_type="application/json"
    )
    assert res2.status_code == 201
    dataset2 = Dataset.objects.get(id=res2.data["id"])

    dataset_a_json["title"] = {"en": "new_title"}
    res3 = admin_client.put(
        f"/v3/datasets/{res2.data['id']}", dataset_a_json, content_type="application/json"
    )
    assert res3.status_code == 200
    assert len(res3.data["other_versions"]) == 1
    assert len(res3.data["field_of_science"]) == 1

    # Ensure objects are separate copies where required
    assert dataset1.id != dataset2.id
    assert list(dataset1.field_of_science.all()) == list(dataset2.field_of_science.all())
    assert list(dataset1.theme.all()) == list(dataset2.theme.all())
    assert list(dataset1.language.all()) == list(dataset2.language.all())
    assert dataset1.access_rights.id != dataset2.access_rights.id
    assert dataset1.access_rights.license.first().id != dataset2.access_rights.license.first().id
    assert list(dataset1.temporal.all()) != list(dataset2.temporal.all())
    assert list(dataset1.keyword) == list(dataset2.keyword)
