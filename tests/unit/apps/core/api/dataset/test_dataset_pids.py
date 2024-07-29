from unittest import mock

import pytest

from apps.core.models import Dataset
from apps.core.services.pid_ms_client import PIDMSClient, ServiceUnavailableError

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


# Create a dataset with PID into a harvested catalog
# Check that PID is saved properly
def test_create_harvested_dataset_with_pid(
    admin_client, dataset_a_json, datacatalog_harvested_json, reference_data
):
    dataset = dataset_a_json
    dataset["data_catalog"] = datacatalog_harvested_json["id"]
    dataset["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
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
def test_create_harvested_dataset_without_pid(
    admin_client, dataset_a_json, datacatalog_harvested_json, reference_data
):
    dataset = dataset_a_json
    dataset["data_catalog"] = datacatalog_harvested_json["id"]
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert (
        "Dataset in a harvested catalog has to have a persistent identifier"
        in res.json()["persistent_identifier"]
    )


# Try to create a dataset with PID into a non-harvested catalog
# Check that dataset creation results into an error
def test_create_dataset_with_pid(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400


# Create a dataset with pid_type=URN
# Check that it is generated
def test_create_dataset_with_urn(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["pid_type"] = "URN"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid is not None

    # Check that PID stays the same after the dataset has been updated
    new_title = {"title": {"en": "updated title"}}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_title, content_type="application/json")
    assert res.json().get("persistent_identifier", None) == pid

    # Try to update the PID
    # Check that it fails
    new_pid = {"persistent_identifier": "new_pid"}
    res = admin_client.patch(f"/v3/datasets/{ds_id}", new_pid, content_type="application/json")
    assert res.status_code == 400


# Create a dataset with pid_type=DOI
# Check that it is generated
# Try to add remote_resources
# Check that dataset update results into an error
# Check that remote resources are not added
def test_create_dataset_with_doi(admin_client, dataset_a_json, data_catalog, reference_data):
    pytest.xfail("PID MS - DOI implementation missing")
    dataset = dataset_a_json
    dataset["pid_type"] = "DOI"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    assert res.json().pop("persistent_identifier", None) is not None
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


# Create a draft dataset
# Check that it does not have PID
# Publish the draft
# Check that it has a PID
def test_create_draft_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["pid_type"] = "URN"
    dataset.pop("persistent_identifier", None)
    dataset["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid is None

    res2 = admin_client.post(f"/v3/datasets/{ds_id}/publish", content_type="application/json")
    pid2 = res2.json().get("persistent_identifier", None)
    assert pid2 is not None


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
def test_create_dataset_with_failed_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, patch_mock_create_urn_fail
):
    old_count = Dataset.available_objects.all().count()
    dataset = dataset_a_json
    dataset["pid_type"] = "URN"
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
def test_new_version_has_no_pid(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = dataset_a_json
    dataset["pid_type"] = "URN"
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    pid = res.json().get("persistent_identifier", None)
    ds_id = res.json().get("id", None)
    assert pid is not None

    res2 = admin_client.post(f"/v3/datasets/{ds_id}/new-version")
    assert res2.status_code == 201
    pid2 = res2.json().get("persistent_identifier", None)
    ds_id2 = res2.json().get("id", None)
    assert pid2 is None

    res3 = admin_client.post(f"/v3/datasets/{ds_id2}/publish", content_type="application/json")
    pid3 = res3.json().get("persistent_identifier", None)
    assert pid3 is not None
    assert pid3 != pid


# Create a dataset
# Try to create the same dataset again
# Check that error message is correct
def test_create_dataset_with_existing_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Data catalog is not allowed to have multiple datasets with same value" in str(
        res.data["persistent_identifier"]
    )


# Create a dataset
# Soft-delete the dataset
# Try to create the same dataset again
# Check that error message is correct
def test_create_dataset_with_existing_soft_deleted_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    res = admin_client.delete(f"/v3/datasets/{ds_id}")
    assert res.status_code == 204

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Data catalog is not allowed to have multiple datasets with same value" in str(
        res.data["persistent_identifier"]
    )


# Create a dataset
# Hard-delete the dataset
# Create the same dataset again
# Check that status code is correct
def test_create_dataset_with_previously_hard_deleted_pid(
    admin_client, dataset_a_json, data_catalog, reference_data, datacatalog_harvested_json
):
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_a_json["persistent_identifier"] = "some_pid"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    res = admin_client.delete(f"/v3/datasets/{ds_id}?flush=True")
    assert res.status_code == 204

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


# Try to create a dataset without pid_type and pid
# Check that request fails
def test_create_dataset_without_pid_type_and_pid_fails(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset = dataset_a_json
    dataset.pop("pid_type", None)
    dataset.pop("persistent_identifier", None)
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code != 201


# Create a dataset
# Try to update the dataset using put without pid_type and pid
# Check that request fails
def test_update_dataset_without_pid_type_and_pid_fails(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset = dataset_a_json
    dataset["pid_type"] = "URN"
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201
    ds_id = res.json().get("id", None)

    dataset.pop("pid_type", None)
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
