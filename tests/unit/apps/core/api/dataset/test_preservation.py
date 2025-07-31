import pytest
from tests.utils import assert_nested_subdict, matchers

from apps.core.models.catalog_record.dataset import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def preservation_dataset_json(dataset_a_json, contract_a):
    dataset = {
        **dataset_a_json,
        "preservation": {
            "contract": contract_a.json()["id"],
            "state": 0,
            "description": {"en": "Test preservation description"},
            "reason_description": "Test preservation reason description",
        },
    }
    return dataset


@pytest.fixture
def preservation_dataset(admin_client, preservation_dataset_json):
    return admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    ).json()


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_preservation(admin_client, preservation_dataset_json):
    resp = admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert_nested_subdict(preservation_dataset_json["preservation"], data["preservation"])
    assert data["preservation"]["preservation_identifier"] == data["persistent_identifier"]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_preservation_nondefault_preservation_identifier(
    admin_client, preservation_dataset_json
):
    preservation_dataset_json["preservation"]["preservation_identifier"] = "explicitly-set-value"
    resp = admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 201
    assert resp.data["preservation"]["preservation_identifier"] == "explicitly-set-value"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_preservation_clear_preservation_identifier(
    admin_client, preservation_dataset_json
):
    preservation_dataset_json["preservation"]["preservation_identifier"] = "explicitly-set-value"
    resp = admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 201
    dataset_id = resp.data["id"]
    pid = resp.data["persistent_identifier"]
    assert resp.data["preservation"]["preservation_identifier"] == "explicitly-set-value"

    # Clear preservation identifier -> reverts to pid
    resp = admin_client.patch(
        f"/v3/datasets/{dataset_id}/preservation",
        {"preservation_identifier": None},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.data["preservation_identifier"] == pid

    # Ensure the updated preservation value is saved
    resp = admin_client.get(
        f"/v3/datasets/{dataset_id}/preservation",
        content_type="application/json",
    )
    assert resp.data["preservation_identifier"] == pid


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_preservation_non_pas(ida_client, preservation_dataset_json):
    resp = ida_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.json()["preservation"] == "Only PAS users are allowed to set preservation"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_non_pas(ida_client, contract_a, dataset_a_json):
    resp = ida_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 201
    id = resp.json()["id"]
    resp = ida_client.patch(
        f"/v3/datasets/{id}",
        {
            "preservation": {
                "contract": contract_a.json()["id"],
                "state": 10,
                "description": {"en": "Test preservation description"},
                "reason_description": "Test preservation reason description",
            },
        },
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["preservation"] == "Only PAS users are allowed to set preservation"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_dataset_preservation_cumulative_state(admin_client, preservation_dataset_json):
    preservation_dataset_json["cumulative_state"] = 1
    preservation_dataset_json["preservation"]["state"] = 10
    resp = admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 400
    assert "Cumulative datasets are not allowed" in resp.json()["cumulative_state"]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_preservation_without_contract(admin_client, preservation_dataset_json):
    """
    Try updating preservation state without including a valid contract;
    this should fail.
    """
    data = preservation_dataset_json.copy()
    del data["preservation"]["contract"]
    resp = admin_client.post("/v3/datasets", data, content_type="application/json")
    assert resp.status_code == 400
    assert resp.json()["preservation"]["contract"] == [
        "Dataset in preservation process must have a contract."
    ]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_state(
    admin_client, preservation_dataset, dataset_signal_handlers
):
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"state": 20},
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == preservation_dataset["preservation"]["id"]
    assert data["state"] == 20
    dataset_signal_handlers.assert_call_counts(created=0, updated=1)


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_state_unknown_state(admin_client, preservation_dataset):
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"state": 262},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == 262


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_invalid_state(admin_client, preservation_dataset):
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"state": "invalid"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["state"] == ["A valid integer is required."]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_state_remove_contract_error(
    admin_client, preservation_dataset
):
    """
    Try updating a dataset to remove the contract while retaining the current
    preservation state. This should fail.
    """
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"contract": None},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["contract"] == ["Dataset in preservation process must have a contract."]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_reset_preservation(admin_client, preservation_dataset):
    """
    Try updating a dataset to reset the preservation process by clearing
    the preservation state and removing the contract
    """
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation?include_nulls=true",
        {"state": -1, "contract": None},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"]
    assert data["state"] == -1
    assert data["contract"] is None


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_query_datasets_preservation_state(admin_client, preservation_dataset):
    """
    Query datasets that have the given preservation state
    """
    # One dataset with state 0
    resp = admin_client.get("/v3/datasets", {"preservation__state": "10,0"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["id"] == preservation_dataset["id"]

    # No datasets with these preservation states
    resp = admin_client.get("/v3/datasets", {"preservation__state": "10,20"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_delete_dataset_with_preservation(admin_client, preservation_dataset):
    """
    Delete a dataset containing preservation data
    """
    resp = admin_client.delete(f"/v3/datasets/{preservation_dataset['id']}")
    assert resp.status_code == 204

    resp = admin_client.get(f"/v3/datasets/{preservation_dataset['id']}")
    assert resp.status_code == 404

    # Contract is NOT deleted
    resp = admin_client.get(f"/v3/contracts/{preservation_dataset['preservation']['contract']}")
    assert resp.status_code == 200


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_preservation_indirect(admin_client, preservation_dataset):
    """
    Try updating dataset's preservation state via the `/v3/datasets/<id>` endpoint
    and ensure preservation data must be complete in order to be accepted
    """
    preservation_dataset = {
        "id": preservation_dataset["id"],
        "preservation": preservation_dataset["preservation"],
    }

    # Attempt to patch only preservation state; this will fail
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}",
        {"id": preservation_dataset["id"], "preservation": {"state": 50}},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json() == {
        "preservation": {"contract": ["Dataset in preservation process must have a contract."]}
    }

    preservation = preservation_dataset["preservation"]

    # Provide both mandatory fields; update should now succeed
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}",
        {
            "id": preservation_dataset["id"],
            "preservation": {"state": 50, "contract": preservation["contract"]},
        },
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["preservation"]["state"] == 50
    assert data["preservation"]["contract"] == preservation["contract"]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_delete_dataset_preservation(admin_client, preservation_dataset):
    """Try deleting dataset preservation using the endpoint."""
    resp = admin_client.delete(
        f"/v3/datasets/{preservation_dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 204

    # The preservation endpoint should return default values when preservation does not exist
    resp = admin_client.get(
        f"/v3/datasets/{preservation_dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_get_dataset_preservation_anonymous(client, preservation_dataset):
    """Try retrieving dataset preservation as an anonymous user."""
    resp = client.get(
        f"/v3/datasets/{preservation_dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 200

    # Nested endpoint of should not be visible if dataset is not visible
    Dataset.objects.filter(id=preservation_dataset["id"]).update(state="draft")
    resp = client.get(
        f"/v3/datasets/{preservation_dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 404


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_get_dataset_nonexisting_preservation(
    admin_client, dataset_a_json, dataset_signal_handlers
):
    """Preservation should return default values when preservation does not exist."""
    dataset = admin_client.post(
        "/v3/datasets", dataset_a_json, content_type="application/json"
    ).json()

    dataset_signal_handlers.reset()
    resp = admin_client.get(
        f"/v3/datasets/{dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 200
    assert resp.data == {
        "reason_description": "",
        "state": -1,
        "pas_package_created": False,
        "pas_process_running": False,
    }
    dataset_signal_handlers.assert_call_counts(created=0, updated=0)


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_patch_dataset_nonexisting_preservation(
    admin_client, dataset_a_json, dataset_signal_handlers
):
    """Try patching preservation object that does not exist yet. Should work like put."""
    dataset = admin_client.post(
        "/v3/datasets", dataset_a_json, content_type="application/json"
    ).json()

    dataset_signal_handlers.reset()
    resp = admin_client.patch(
        f"/v3/datasets/{dataset['id']}/preservation",
        {"reason_description": "testing patch"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert resp.data == {
        "id": matchers.Any(),
        "reason_description": "testing patch",
        "state": -1,
        "pas_package_created": False,
        "pas_process_running": False,
        "preservation_identifier": dataset["persistent_identifier"],
    }
    dataset_signal_handlers.assert_call_counts(created=0, updated=1)

    # Check the created preservation is associated to the dataset
    resp = admin_client.get(
        f"/v3/datasets/{dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 200


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_put_dataset_nonexisting_preservation(
    admin_client, dataset_a_json, dataset_signal_handlers
):
    """Try creating preservation object using put."""
    dataset = admin_client.post(
        "/v3/datasets", dataset_a_json, content_type="application/json"
    ).json()

    dataset_signal_handlers.reset()
    resp = admin_client.put(
        f"/v3/datasets/{dataset['id']}/preservation",
        {"state": -1},
        content_type="application/json",
    )
    assert resp.status_code == 201
    dataset_signal_handlers.assert_call_counts(created=0, updated=1)

    # Check the created preservation is associated to the dataset
    resp = admin_client.get(
        f"/v3/datasets/{dataset['id']}/preservation", content_type="application/json"
    )
    assert resp.status_code == 200


@pytest.fixture
def preservation_dataset_with_fileset(admin_client, preservation_dataset_json):
    preservation_dataset_json["fileset"] = {"storage_service": "ida", "csc_project": "project"}
    return admin_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    ).json()


def test_create_dataset_preservation_version(
    pas_client, preservation_dataset_with_fileset, data_catalog_pas
):
    origin_id = preservation_dataset_with_fileset["id"]
    origin_pid = preservation_dataset_with_fileset["persistent_identifier"]
    res = pas_client.post(
        f"/v3/datasets/{origin_id}/create-preservation-version",
        content_type="application/json",
    )
    assert res.status_code == 201, res.data
    data = res.json()
    preserved_id = data["id"]
    preserved_pid = data["persistent_identifier"]
    preserved_preservation_identifier = data["preservation"]["preservation_identifier"]
    assert preserved_preservation_identifier == preserved_pid
    assert data["data_catalog"] == "urn:nbn:fi:att:data-catalog-pas"
    assert data["fileset"]["storage_service"] == "pas"
    assert data["fileset"]["csc_project"] == "project"
    assert data["preservation"]["dataset_origin_version"]["id"] == origin_id
    assert data["preservation"]["dataset_origin_version"]["preservation_state"] == -1
    assert data["other_identifiers"][0]["notation"] == origin_pid
    assert len(data["dataset_versions"]) == 1

    # Check original version has new dataset relations but is otherwise unchanged
    res = pas_client.get(f"/v3/datasets/{origin_id}", content_type="application/json")
    assert res.status_code == 200, res.data
    data = res.json()
    assert data["data_catalog"] == "urn:nbn:fi:att:data-catalog-ida"
    assert data["fileset"]["storage_service"] == "ida"
    assert data["fileset"]["csc_project"] == "project"
    assert data["preservation"]["dataset_version"]["id"] == preserved_id
    assert data["preservation"]["dataset_version"]["preservation_state"] == 0

    original_preservation_identifier = data["preservation"]["preservation_identifier"]
    assert original_preservation_identifier == data["persistent_identifier"]
    assert original_preservation_identifier != preserved_preservation_identifier
    assert data["other_identifiers"][0]["notation"] == preserved_pid
    assert len(data["dataset_versions"]) == 1


def test_create_dataset_preservation_version_no_preservation(
    pas_client, preservation_dataset_json, data_catalog_pas
):
    preservation_dataset_json.pop("preservation")
    preservation_dataset = pas_client.post(
        "/v3/datasets", preservation_dataset_json, content_type="application/json"
    ).json()
    origin_id = preservation_dataset["id"]
    res = pas_client.post(
        f"/v3/datasets/{origin_id}/create-preservation-version",
        content_type="application/json",
    )
    assert res.status_code == 400, res.data
    data = res.json()
    assert "not in preservation" in data["detail"]


def test_create_dataset_preservation_version_twice(
    admin_client, pas_client, preservation_dataset_with_fileset, data_catalog_pas
):
    origin_id = preservation_dataset_with_fileset["id"]
    res = pas_client.post(
        f"/v3/datasets/{origin_id}/create-preservation-version",
        content_type="application/json",
    )
    assert res.status_code == 201, res.data
    res = pas_client.patch(
        f"/v3/datasets/{origin_id}/preservation", {"state": 0}, content_type="application/json"
    )
    assert res.status_code == 200, res.data
    res = pas_client.post(
        f"/v3/datasets/{origin_id}/create-preservation-version",
        content_type="application/json",
    )
    assert res.status_code == 400, res.data
    assert "already has a PAS version" in res.json()["detail"]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_preservation_pas_process_running(pas_client, ida_client, preservation_dataset):
    # Lock dataset from modifications by non-PAS users
    resp = pas_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"pas_process_running": True},
        content_type="application/json",
    )
    assert resp.status_code == 200

    # Try to patch dataset and nested objects as non-PAS user
    resp = ida_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}", {}, content_type="application/json"
    )
    assert resp.status_code == 423
    assert "Only PAS service is allowed to modify the dataset" in resp.json()["detail"]

    resp = ida_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {},
        content_type="application/json",
    )
    assert resp.status_code == 423
    assert "Only PAS service is allowed to modify the dataset" in resp.json()["detail"]

    # Release dataset PAS lock
    resp = pas_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"pas_process_running": False},
        content_type="application/json",
    )
    assert resp.status_code == 200

    # Try to patch dataset as non-PAS user
    resp = ida_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}", {}, content_type="application/json"
    )
    assert resp.status_code == 200
