import pytest
from tests.utils import assert_nested_subdict

from apps.core.factories import ContractFactory, PreservationFactory

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
    assert_nested_subdict(preservation_dataset_json["preservation"], resp.json()["preservation"])


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
def test_update_dataset_preservation_state(admin_client, preservation_dataset):
    resp = admin_client.patch(
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
        {"state": 20},
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == preservation_dataset["preservation"]["id"]
    assert data["state"] == 20


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
        f"/v3/datasets/{preservation_dataset['id']}/preservation",
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
    resp = admin_client.get("/v3/datasets", {"preservation__state": ["10", "0"]})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["id"] == preservation_dataset["id"]

    # No datasets with these preservation states
    resp = admin_client.get("/v3/datasets", {"preservation__state": ["10", "20"]})
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
