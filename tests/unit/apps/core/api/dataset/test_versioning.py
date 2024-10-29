import logging

import pytest

from apps.core import factories
from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.versioning]

logger = logging.getLogger(__name__)


def _get_dataset_from_dataset_versions(dataset_versions, ds_id):
    for ds in dataset_versions:
        if ds["id"] == ds_id:
            return ds
    return None


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

    # ensure normal user doesn't see version draft
    res = user_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 1
    # but admin does
    res = admin_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2


def test_dataset_version_numbers(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    ds1_id = res1.data["id"]

    res2 = admin_client.post(f"/v3/datasets/{ds1_id}/new-version", content_type="application/json")
    assert res2.status_code == 201
    ds2_id = res2.data["id"]

    # Ensure version numbers are serialized correctly in dataset_versions
    res1 = admin_client.get(f"/v3/datasets/{ds1_id}")
    dataset_versions1 = res1.data["dataset_versions"]
    ds1_version = _get_dataset_from_dataset_versions(dataset_versions1, ds1_id)["version"]
    ds2_version = _get_dataset_from_dataset_versions(dataset_versions1, ds2_id)["version"]
    assert res1.data["version"] == 1
    assert ds1_version == 1
    assert ds2_version == 2

    # Ensure that dataset_versions are identical
    res2 = admin_client.get(f"/v3/datasets/{ds2_id}")
    dataset_versions2 = res2.data["dataset_versions"]
    assert res2.data["version"] == 2
    assert dataset_versions1 == dataset_versions2


def test_creating_version_of_a_draft(admin_client, dataset_c_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_c_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 400
    assert res2.data["state"] == "Cannot make a new version of a draft."


def test_creating_version_in_wrong_catalog(
    admin_client, dataset_a_json, datacatalog_without_versioning, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 400
    assert res2.data["data_catalog"] == "Data catalog doesn't support versioning."


def test_versions_with_removed_datasets(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    # second version, publish
    res = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res.status_code == 201
    res2 = admin_client.post(f"/v3/datasets/{res.data['id']}/publish")
    assert res2.status_code == 200

    # third version, publish
    res = admin_client.post(f"/v3/datasets/{res2.data['id']}/new-version")
    assert res.status_code == 201
    res3 = admin_client.post(f"/v3/datasets/{res.data['id']}/publish")
    assert res3.status_code == 200

    # delete third version
    res = admin_client.delete(f"/v3/datasets/{res3.data['id']}")
    assert res.status_code == 204

    # try to create a new version from version 3
    res3 = admin_client.post(f"/v3/datasets/{res3.data['id']}/new-version")
    assert res3.status_code == 404

    # create a new version from version 2
    res = admin_client.post(f"/v3/datasets/{res2.data['id']}/new-version")
    assert res.status_code == 201


def test_creating_new_version_of_not_latest_dataset(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 201

    res3 = admin_client.post(f"/v3/datasets/{res2.data['id']}/publish")
    assert res3.status_code == 200

    res4 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res4.status_code == 400
    assert (
        res4.data["dataset_versions"]
        == "Newer version of this dataset exists. Only the latest existing version of the dataset can be used to make a new version."
    )


def test_creating_new_version_with_existing_version_draft(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res2.status_code == 201

    res3 = admin_client.post(f"/v3/datasets/{res1.data['id']}/new-version")
    assert res3.status_code == 400
    assert (
        res3.data["dataset_versions"]
        == "There is an existing draft of a new version of this dataset."
    )


def test_version_draft_permissions(
    admin_client, user_client, user_client_2, dataset_a_json, data_catalog, reference_data
):
    # user1 creates a dataset
    res1 = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    assert res1.data["version"] == 1
    ds1_id = res1.data["id"]

    # user1 creates a second version
    res2 = user_client.post(f"/v3/datasets/{ds1_id}/new-version")
    assert res2.status_code == 201
    assert res2.data["version"] == 2
    ds2_id = res2.data["id"]

    # ensure user1 can see the second version draft in dataset_versions
    res = user_client.get(f"/v3/datasets/{ds1_id}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2

    # ensure user2 cannot see the second version draft in dataset_versions
    res = user_client_2.get(f"/v3/datasets/{ds1_id}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 1

    # user1 publishes the second version draft
    res = user_client.post(f"/v3/datasets/{ds2_id}/publish")
    assert res.status_code == 200
    assert res.data["version"] == 2

    # ensure user2 can see it now
    res = user_client_2.get(f"/v3/datasets/{ds1_id}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2

    # user1 creates a draft of edits of second version
    res3 = user_client.post(f"/v3/datasets/{ds2_id}/create-draft")
    assert res3.status_code == 201
    assert res3.data["version"] == 2
    ds3_id = res3.data["id"]

    # ensure user1 can see the draft information
    res = user_client.get(f"/v3/datasets/{ds1_id}?include_nulls=true")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 3
    assert "next_draft" in res.data["dataset_versions"][1].keys()

    # ensure user2 cannot see this information
    res = user_client_2.get(f"/v3/datasets/{ds1_id}?include_nulls=true")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2
    assert "next_draft" not in res.data["dataset_versions"][1].keys()

    # user1 makes yet another version (3)
    res4 = user_client.post(f"/v3/datasets/{ds2_id}/new-version?include_nulls=true")
    assert res4.status_code == 201
    ds4_id = res4.data["id"]

    # ensure version numbering is correct even with all the drafts (v2 edit draft and v3 version draft)
    assert res4.data["version"] == 3

    # ensure correct amount of versions is shown to both users (2 published, 2 drafts)
    assert len(res4.data["dataset_versions"]) == 4

    res = user_client_2.get(f"/v3/datasets/{ds1_id}")
    assert res.status_code == 200
    assert len(res.data["dataset_versions"]) == 2

    # ensure that version numbers are serialized correctly
    res1 = admin_client.get(f"/v3/datasets/{ds1_id}")
    res2 = admin_client.get(f"/v3/datasets/{ds2_id}")
    res3 = admin_client.get(f"/v3/datasets/{ds3_id}")
    res4 = admin_client.get(f"/v3/datasets/{ds4_id}")

    ds1_version = res1.data["version"]
    ds2_version = res2.data["version"]
    ds3_version = res3.data["version"]
    ds4_version = res4.data["version"]

    assert ds1_version == 1
    assert ds2_version == 2
    assert ds3_version == 2
    assert ds4_version == 3

    # ensure that version numbers in dataset_versions are serialized correctly
    ds1_versions = res1.data["dataset_versions"]
    ds2_versions = res2.data["dataset_versions"]
    ds3_versions = res3.data["dataset_versions"]
    ds4_versions = res4.data["dataset_versions"]

    ds1_version = _get_dataset_from_dataset_versions(ds1_versions, ds1_id)["version"]
    ds2_version = _get_dataset_from_dataset_versions(ds1_versions, ds2_id)["version"]
    ds3_version = _get_dataset_from_dataset_versions(ds1_versions, ds3_id)["version"]
    ds4_version = _get_dataset_from_dataset_versions(ds1_versions, ds4_id)["version"]

    assert ds1_version == 1
    assert ds2_version == 2
    assert ds3_version == 2
    assert ds4_version == 3

    # ensure that dataset_versions are identical
    assert ds1_versions == ds2_versions
    assert ds1_versions == ds3_versions
    assert ds1_versions == ds4_versions


@pytest.mark.usefixtures("reference_data", "data_catalog")
def test_list_latest_versions(admin_client, user_client, dataset_a_json):
    # Create published dataset + another with 2 published and 1 draft version
    dataset_a_json["title"] = {"en": "dataset"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201

    dataset_a_json["title"] = {"en": "version 1 something"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201

    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/new-version", content_type="application/json"
    )
    assert res.status_code == 201

    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"title": {"en": "version 2"}},
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/publish",
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.post(
        f"/v3/datasets/{res.data['id']}/new-version", content_type="application/json"
    )
    assert res.status_code == 201

    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"title": {"en": "version 3 draft"}},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Admin should see latest versions even if they are drafts
    res = admin_client.get("/v3/datasets?latest_versions=true&ordering=created&pagination=false")
    assert res.status_code == 200
    assert len(res.data) == 2
    assert res.data[0]["title"]["en"] == "dataset"
    assert res.data[1]["title"]["en"] == "version 3 draft"

    # Ordering should work
    res = admin_client.get("/v3/datasets?latest_versions=true&ordering=-created&pagination=false")
    assert res.status_code == 200
    assert res.data[0]["title"]["en"] == "version 3 draft"
    assert res.data[1]["title"]["en"] == "dataset"

    # Filtering should match any latest dataset
    res = admin_client.get("/v3/datasets?latest_versions=true&pagination=false&title=something")
    assert res.status_code == 200
    assert len(res.data) == 0

    res = admin_client.get("/v3/datasets?latest_versions=true&pagination=false&search=draft")
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["title"]["en"] == "version 3 draft"

    # Other user should only see published versions
    res = user_client.get("/v3/datasets?latest_versions=true&ordering=created&pagination=false")
    assert res.status_code == 200
    assert len(res.data) == 2
    assert res.data[0]["title"]["en"] == "dataset"
    assert res.data[1]["title"]["en"] == "version 2"
