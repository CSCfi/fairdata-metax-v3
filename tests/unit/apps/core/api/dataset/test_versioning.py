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


def test_dataset_versions(admin_client, user_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    dataset1 = Dataset.objects.get(id=res1.data["id"])

    res2 = admin_client.post(
        f"/v3/datasets/{res1.data['id']}/new-version", content_type="application/json"
    )
    assert res2.status_code == 201
    dataset2 = Dataset.objects.get(id=res2.data["id"])

    dataset_a_json["title"] = {"en": "new_title"}
    dataset_a_json["state"] = "draft"
    res3 = admin_client.put(
        f"/v3/datasets/{res2.data['id']}", dataset_a_json, content_type="application/json"
    )
    assert res3.status_code == 200
    assert len(res3.data["dataset_versions"]) == 2
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

    #ensure normal user doesn't see version draft
    res = user_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 1
    #but admin does
    res = admin_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2

def test_creating_version_of_a_draft(admin_client, dataset_c_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_c_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 400
    assert res2.data["state"] == "Cannot make a new version of a draft."

def test_creating_version_in_wrong_catalog(admin_client, dataset_a_json, datacatalog_without_versioning, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 400
    assert res2.data["data_catalog"] == "Data catalog doesn't support versioning."

def test_versions_with_removed_datasets(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    #second version, publish
    res = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res.status_code == 201
    res2 = admin_client.post(f"/v3/datasets/{res.data['id']}/publish")
    assert res2.status_code == 200

    #third version, publish
    res = admin_client.post(f"/v3/datasets/{res2.data['id']}/new-version")
    assert res.status_code == 201
    res3 = admin_client.post(f"/v3/datasets/{res.data['id']}/publish")
    assert res3.status_code == 200

    #delete third version
    res = admin_client.delete(f"/v3/datasets/{res3.data['id']}")
    assert res.status_code == 204

    #try to create a new version from version 3
    res3 = admin_client.post(f"/v3/datasets/{res3.data['id']}/new-version")
    assert res3.status_code == 404

    #create a new version from version 2
    res = admin_client.post(f"/v3/datasets/{res2.data['id']}/new-version")
    assert res.status_code == 201

def test_creating_new_version_of_not_latest_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 201

    res3 = admin_client.post(f"/v3/datasets/{res2.data['id']}/publish")
    assert res3.status_code == 200

    res4 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res4.status_code == 400
    assert res4.data["dataset_versions"] == "Newer version of this dataset exists. Only the latest existing version of the dataset can be used to make a new version."

def test_creating_new_version_with_existing_version_draft(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 201

    res3 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res3.status_code == 400
    assert res3.data["dataset_versions"] == "There is an existing draft of a new version of this dataset."

def test_version_draft_permissions(admin_client, user_client, user_client_2, dataset_a_json, data_catalog, reference_data):
    #user1 creates a dataset
    res1 = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    assert res1.data["version"] == 1

    #user1 creates a second version
    res2 = user_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 201
    assert res2.data["version"] == 2

    #ensure user1 can see the second version draft in dataset_versions
    res = user_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 2

    #ensure user2 cannot see the second version draft in dataset_versions
    res = user_client_2.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 1

    #user1 publishes the second version draft
    res = user_client.post(f"/v3/datasets/{res2.data['id']}/publish")
    assert res.status_code == 200
    assert res.data["version"] == 2

    #ensure user2 can see it now
    res = user_client_2.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 2

    #user1 creates a draft of edits of second version
    res3 = user_client.post(f"/v3/datasets/{res2.data['id']}/create-draft")
    assert res3.status_code == 201
    assert res3.data["version"] == 2

    #ensure user1 can see the draft information
    res = user_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 3
    assert 'next_draft' in res.data['dataset_versions'][1].keys()

    #ensure user2 cannot see this information
    res = user_client_2.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 2
    assert 'next_draft' not in res.data['dataset_versions'][1].keys()

    #user1 makes yet another version (3)
    res = user_client.post(f"/v3/datasets/{res2.data['id']}/new-version")
    assert res.status_code == 201

    #ensure version numbering is correct even with all the drafts (v2 edit draft and v3 version draft)
    assert res.data['version'] == 3

    #ensure correct amount of versions is shown to both users (2 published, 2 drafts)
    assert len(res.data['dataset_versions']) == 4

    res = user_client_2.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data['dataset_versions']) == 2