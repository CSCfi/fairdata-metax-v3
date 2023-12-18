import logging

import pytest

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

    res2 = admin_client.post(
        f"/v3/datasets/{res1.data['id']}/new-version", content_type="application/json"
    )
    assert res2.status_code == 201

    dataset_a_json["title"] = {"en": "new_title"}
    res3 = admin_client.put(
        f"/v3/datasets/{res2.data['id']}", dataset_a_json, content_type="application/json"
    )
    assert res3.status_code == 200
    assert len(res3.data["other_versions"]) == 1
