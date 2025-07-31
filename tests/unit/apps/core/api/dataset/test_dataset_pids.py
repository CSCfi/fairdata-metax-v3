import json
import re
import uuid
from datetime import datetime
from unittest import mock

import pytest
from django.test import override_settings

from apps.core.models import Dataset
from apps.core.services.pid_ms_client import PIDMSClient, ServiceUnavailableError

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


# Create a dataset with PID into a harvested catalog
# Check that PID is saved properly
def test_create_harvested_dataset_with_PID(
    admin_client, dataset_a_json, datacatalog_harvested_json, reference_data
):
    dataset = dataset_a_json
    dataset["data_catalog"] = datacatalog_harvested_json["id"]
    dataset["persistent_identifier"] = "some_pid"
    dataset["generate_pid_on_publish"] = None
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201, res.data
    assert res.json()["persistent_identifier"] == "some_pid"
    ds_id = res.json()["id"]

    # Try to update the dataset title
    # Check that pid is still the same
    new_title = {"title": {"en": "updated title"}}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_title, content_type="application/json")
    assert res.status_code == 200
    assert res.json()["persistent_identifier"] == "some_pid"

    # Try to update the dataset pid
    # Check that pid has been updated
    new_pid = {"persistent_identifier": "new_pid"}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_pid, content_type="application/json")
    assert res.status_code == 200
    assert res.json()["persistent_identifier"] == "new_pid"


# Create a dataset without PID into a harvested catalog
# Check that dataset creation results into an error
def test_create_harvested_dataset_without_PID(
    admin_client, dataset_a_json, datacatalog_harvested_json, reference_data
):
    dataset = dataset_a_json
    dataset["data_catalog"] = datacatalog_harvested_json["id"]
    dataset.pop("persistent_identifier", None)
    dataset.pop("generate_pid_on_publish", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert (
        "Dataset has to have a persistent identifier when publishing"
        in res.json()["persistent_identifier"]
    )


# Try to create a dataset with PID into a non-harvested catalog
# Check that dataset creation results into an error
def test_create_dataset_with_PID(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400


# Create a dataset with generate_pid_on_publish=URN
# Check that it is generated
def test_create_dataset_with_URN(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid.startswith("urn:")

    # Check that PID stays the same after the dataset has been updated
    new_title = {"title": {"en": "updated title"}}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_title, content_type="application/json")
    assert res.json().get("persistent_identifier", None) == pid

    # Try to update the PID
    # Check that it fails
    new_pid = {"persistent_identifier": "new_pid"}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_pid, content_type="application/json")
    assert res.status_code == 400


# Create a dataset with generate_pid_on_publish=DOI
# Check that it is generated
# Try to add remote_resources
# Check that dataset update results into an error
# Check that remote resources are not added
def test_create_dataset_with_doi(
    admin_client, dataset_maximal_json, data_catalog, reference_data, mock_pid_ms
):
    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    assert res.json().pop("persistent_identifier", None).startswith("doi:")
    ds_id = res.json()["id"]
    remote_resources = [
        {
            "title": {"en": "Remote Resource"},
            "access_url": "https://access.url",
            "download_url": "https://download.url",
            "use_category": {
                "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
            },
            "file_type": {"url": "http://uri.suomi.fi/codelist/fairdata/file_type/code/video"},
            "checksum": "md5:f00f",
            "mediatype": "text/csv",
        }
    ]
    res = admin_client.patch(
        f"/v3/datasets/{ds_id}", remote_resources, content_type="application/json"
    )
    assert res.status_code == 400


@override_settings(PID_MS_CLIENT_INSTANCE="apps.core.services.pid_ms_client._PIDMSClient")
def test_create_dataset_with_doi_fail(
    admin_client, dataset_maximal_json, data_catalog, reference_data
):
    dataset = dataset_maximal_json
    dataset["state"] = "published"
    dataset["generate_pid_on_publish"] = "DOI"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503


# Create a draft dataset
# Check that it does not have PID
# Publish the draft
# Check that it has a PID
def test_create_draft_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset.pop("persistent_identifier", None)
    dataset["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid == None

    res2 = admin_client.post(f"/v3/datasets/{ds_id}/publish", content_type="application/json")
    pid2 = res2.json().get("persistent_identifier", None)
    assert pid2 != None


def mock_create_urn_fail(self):
    raise (ServiceUnavailableError("PID creation failed"))


@pytest.fixture()
def patch_mock_create_urn_fail():
    with mock.patch.object(PIDMSClient, "create_urn", mock_create_urn_fail) as _fixture:
        yield _fixture


# Try to create a dataset, but PID MS fails
# Check that error message is correct
# Check that dataset is not created
@pytest.mark.django_db
def test_create_dataset_with_failed_PID(
    admin_client, dataset_a_json, data_catalog, reference_data, mock_pid_ms_fail
):
    old_count = Dataset.available_objects.all().count()
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503
    new_count = Dataset.all_objects.all().count()
    assert new_count == old_count


# Create a dataset
# Check that it has a pid
# Create a new version of the dataset
# Check that it does not have a pid
# Publish the new version
# Check that it has a PID
def test_new_version_has_no_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, mock_pid_ms
):
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid != None

    res2 = admin_client.post(f"/v3/datasets/{ds_id}/new-version")
    assert res2.status_code == 201
    pid2 = res2.json().get("persistent_identifier", None)
    ds_id2 = res2.json().get("id", None)
    assert pid2 == None

    res3 = admin_client.post(f"/v3/datasets/{ds_id2}/publish", content_type="application/json")
    pid3 = res3.json().get("persistent_identifier", None)
    assert pid3 != None
    assert pid3 != pid


# Create a dataset
# Try to create the same dataset again
# Check that error message is correct
def test_create_dataset_with_existing_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_a_json["generate_pid_on_publish"] = None
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Value already exists in the data catalog" in str(res.data["persistent_identifier"])


# Create a dataset in IDA catalog
# Try to create the same PID in another catalog
# Check that error message is correct
def test_create_dataset_with_existing_pid_in_ida_catalog(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = str(res.data["persistent_identifier"])
    dataset_a_json["generate_pid_on_publish"] = None

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Value already exists in IDA or ATT catalog" in str(res.data["persistent_identifier"])


# Create a DOI dataset in IDA catalog
# Try to create the same DOI using different display representation in another catalog
def test_create_dataset_with_same_doi_in_ida_catalog(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["generate_pid_on_publish"] = "DOI"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    modified_doi = str(res.data["persistent_identifier"]).replace("doi:", "https://doi.org/")
    dataset_a_json["persistent_identifier"] = modified_doi
    dataset_a_json["generate_pid_on_publish"] = None
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Value already exists in IDA or ATT catalog" in str(res.data["persistent_identifier"])


# Create a dataset
# Soft-delete the dataset
# Try to create the same dataset again
# Check that error message is correct
def test_create_dataset_with_existing_soft_deleted_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_a_json["generate_pid_on_publish"] = None
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    res = admin_client.delete(f"/v3/datasets/{ds_id}")
    assert res.status_code == 204

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Value already exists in the data catalog" in str(res.data["persistent_identifier"])


# Create a dataset
# Hard-delete the dataset
# Create the same dataset again
# Check that status code is correct
def test_create_dataset_with_previously_hard_deleted_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_a_json["generate_pid_on_publish"] = None
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    res = admin_client.delete(f"/v3/datasets/{ds_id}?flush=True")
    assert res.status_code == 204

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


# Try to create a dataset without generate_pid_on_publish and pid
# Check that request fails
def test_create_dataset_without_generate_pid_on_publish_and_pid_fails(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset = dataset_a_json
    dataset.pop("generate_pid_on_publish", None)
    dataset.pop("persistent_identifier", None)
    dataset.pop("generate_pid_on_publish", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code != 201


# Create a dataset
# Try to update the dataset using put without generate_pid_on_publish and pid
# Check that request fails
def test_update_dataset_without_generate_pid_on_publish_and_pid_fails(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "URN"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    dataset.pop("generate_pid_on_publish", None)
    dataset.pop("persistent_identifier", None)
    res = admin_client.put(f"/v3/datasets/{ds_id}", dataset, content_type="application/json")
    assert res.status_code != 200


# Create a dataset
# Try to update the pid of the dataset
# Check that request fails
# Check that pid is still the same
def test_pid_cant_be_updated(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)
    ds_pid = res.json().get("persistent_identifier", None)

    dataset["persistent_identifier"] = "new_pid"
    res = admin_client.put(f"/v3/datasets/{ds_id}", dataset, content_type="application/json")
    assert res.status_code != 200

    res2 = admin_client.get(f"/v3/datasets/{ds_id}", content_type="application/json")
    ds_pid2 = res2.json().get("persistent_identifier", None)
    assert ds_pid == ds_pid2


# Create a dataset
# Try to update the pid of the dataset
# Check that request fails
# Check that pid is still the same
def test_external_pid_update_draft(
    admin_client, dataset_a_json, data_catalog_harvested, reference_data
):
    dataset = dataset_a_json
    dataset["data_catalog"] = data_catalog_harvested.id
    dataset["generate_pid_on_publish"] = None
    dataset["persistent_identifier"] = "original-pid"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.data.get("id")
    assert res.data.get("persistent_identifier") == "original-pid"

    res = admin_client.post(
        f"/v3/datasets/{ds_id}/create-draft", dataset, content_type="application/json"
    )
    assert res.status_code == 201
    draft_id = res.data.get("id")
    assert res.data.get("persistent_identifier") == "draft:original-pid"

    res = admin_client.patch(
        f"/v3/datasets/{draft_id}",
        {"persistent_identifier": "new-pid"},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data.get("persistent_identifier") == "new-pid"

    res = admin_client.post(f"/v3/datasets/{draft_id}/publish", content_type="application/json")
    assert res.status_code == 200
    assert res.data.get("persistent_identifier") == "new-pid"

    res = admin_client.get(f"/v3/datasets/{ds_id}", content_type="application/json")
    assert res.data.get("persistent_identifier") == "new-pid"


# The deprecated pid_type field should be ignored
def test_pid_type_removed(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["generate_pid_on_publish"] = "DOI"
    dataset_a_json["pid_type"] = "URN"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    assert "pid_type" not in res.data
    assert dataset.generate_pid_on_publish == "DOI"


# Create a dataset with generate_pid_on_publish=DOI
# Update that dataset
def test_update_dataset_with_doi(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    from deepdiff import DeepDiff

    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json()["id"]
    dataset["persistent_identifier"] = res.json()["persistent_identifier"]
    res = admin_client.put(f"/v3/datasets/{ds_id}", dataset, content_type="application/json")
    assert res.status_code == 200
    doi = dataset["persistent_identifier"].replace("doi:", "")
    call = requests_mock.request_history[2]
    payload = json.loads(call.text)
    original = pid_update_payload
    original["data"]["attributes"]["url"] = f"https://{settings.ETSIN_URL}/dataset/{ds_id}"
    original["data"]["attributes"]["identifiers"].append(
        {"identifier": doi, "identifierType": "DOI"}
    )
    assert DeepDiff(payload, original) == {}


# Create a dataset with DOI from Metax V2
# Update that dataset in V3
# Assert that datasets gets updated in PID MS
@override_settings(PID_MS_CLIENT_INSTANCE="apps.core.services.pid_ms_client._PIDMSClient")
def test_update_dataset_with_doi_from_v2(
    legacy_dataset_a_json,
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    from deepdiff import DeepDiff

    # Create legacy dataset
    pid = f"doi:10.23729/{str(uuid.uuid4())}"
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["preferred_identifier"] = pid
    legacy_dataset_a_json["dataset_json"]["data_catalog"] = {
        "identifier": "urn:nbn:fi:att:data-catalog-ida"
    }
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    ds_id = res.json()["id"]

    # Update dataset in V3
    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["persistent_identifier"] = pid
    res = admin_client.put(f"/v3/datasets/{ds_id}", dataset, content_type="application/json")
    assert res.status_code == 200

    # Assert that PID has been inserted to PID MS
    doi = dataset["persistent_identifier"].replace("doi:", "")
    call = requests_mock.request_history[1]
    assert call.path == f"/v1/pid/{doi}"
    assert call.method == "POST"

    # Assert that PID has been updated to PID MS
    call = requests_mock.request_history[2]
    payload = json.loads(call.text)
    original = pid_update_payload
    original["data"]["attributes"]["url"] = f"https://{settings.ETSIN_URL}/dataset/{ds_id}"
    original["data"]["attributes"]["identifiers"].append(
        {"identifier": doi, "identifierType": "DOI"}
    )
    assert call.path == f"/v1/pid/doi/{doi}"
    assert call.method == "PUT"
    assert DeepDiff(payload, original) == {}


# Create draft from a published DOI dataset, update the draft
# Assert that updating creating and updating the draft does not trigger any pidms calls
def test_update_draft_with_doi(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json()["id"]
    assert requests_mock.call_count == 1

    # Create and update draft
    res = admin_client.post(
        f"/v3/datasets/{ds_id}/create-draft", dataset, content_type="application/json"
    )
    assert res.status_code == 201
    draft_id = res.json()["id"]
    res = admin_client.patch(
        f"/v3/datasets/{draft_id}",
        {"title": {"en": "draftia muutan"}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert requests_mock.call_count == 1


# Try to create a dataset with DOI, but it fails in PID MS
# Assert that error is correct
def test_create_dataset_with_doi_pid_ms_error(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    matcher = re.compile(f"https://{settings.PID_MS_BASEURL}/v1/pid/doi")
    requests_mock.register_uri("POST", matcher, status_code=400)

    # Try to create a dataset with DOI

    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503
    assert (
        res.json()["detail"]
        == "Error when creating persistent identifier. Please try again later."
    )


# Try to create a dataset with URN, but it fails in PID MS
# Assert that error is correct
def test_create_dataset_with_urn_pid_ms_error(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms_fail,
):
    # Try to create a dataset with URN

    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503
    assert (
        res.json()["detail"]
        == "Error when creating persistent identifier. Please try again later."
    )


# Try to create a dataset with DOI, but PID MS returns empty string
# Assert that error is correct
def test_create_dataset_with_urn_pid_ms_returns_empty(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    matcher = re.compile(f"https://{settings.PID_MS_BASEURL}/v1/pid/doi")
    requests_mock.register_uri("POST", matcher, text="", status_code=200)

    # Try to create a dataset with URN

    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503
    assert (
        res.json()["detail"]
        == "Error when creating persistent identifier. Please try again later."
    )


# Try to create a dataset with URN, but PID MS returns empty string
# Assert that error is correct
def test_create_dataset_with_urn_pid_ms_returns_empty(
    settings,
    requests_mock,
    admin_client,
    dataset_maximal_json,
    pid_update_payload,
    data_catalog,
    reference_data,
    mock_pid_ms,
):
    matcher = re.compile(f"https://{settings.PID_MS_BASEURL}/v1/pid")
    requests_mock.register_uri("POST", matcher, text="", status_code=200)

    # Try to create a dataset with URN

    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "URN"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 503
    assert (
        res.json()["detail"]
        == "Error when creating persistent identifier. Please try again later."
    )


# Using dummy pid client
# Create a dataset with generate_pid_on_publish=DOI
# Update that dataset
@override_settings(PID_MS_CLIENT_INSTANCE="apps.core.services.pid_ms_client._DummyPIDMSClient")
def test_update_dataset_with_doi_dummy_client(
    admin_client, dataset_maximal_json, data_catalog, reference_data
):
    dataset = dataset_maximal_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset["state"] = "published"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json()["id"]
    dataset["persistent_identifier"] = res.json()["persistent_identifier"]
    res = admin_client.put(f"/v3/datasets/{ds_id}", dataset, content_type="application/json")
    assert res.status_code == 200


# Create a draft DOI dataset
# Check that it does not have PID and issued
# Publish dataset
# Check that it has a publicationYear in payload
@override_settings(PID_MS_CLIENT_INSTANCE="apps.core.services.pid_ms_client._PIDMSClient")
def test_create_draft_dataset_and_publish(
    requests_mock, admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset = dataset_a_json
    dataset["generate_pid_on_publish"] = "DOI"
    dataset.pop("persistent_identifier", None)
    dataset.pop("issued", None)
    dataset["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid == None

    res2 = admin_client.post(f"/v3/datasets/{ds_id}/publish", content_type="application/json")
    call = requests_mock.request_history[0]
    payload = json.loads(call.text)
    assert payload["data"]["attributes"]["publicationYear"] == str(datetime.now().year)
