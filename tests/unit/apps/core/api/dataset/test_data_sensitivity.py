import pytest

from apps.core.factories import ContractFactory, SensitivityRationaleFactory
from apps.core.models.contract import ContractSensitivityRationale
from apps.core.models.catalog_record.dataset import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.contract, pytest.mark.dataset]


@pytest.fixture
def sensitive_contract():
    contract = ContractFactory(
        is_sensitive=True
    )

    contract_rationale = ContractSensitivityRationale(
        rationale=SensitivityRationaleFactory(),
        expiration_date=None,
        contract=contract
    )
    contract_rationale.save()

    return contract


@pytest.fixture
def sensitive_dataset_json(dataset_a_json, reference_data, data_catalog, sensitive_contract):
    dataset = {
        **dataset_a_json,
        "preservation": {
            "contract": sensitive_contract.id,
        },
        "data_sensitivity": {
            "is_sensitive": True,
            "rationales": [
                {
                    "rationale": {"url": sensitive_contract.rationales.first().rationale.url},
                    "expiration_date": "2027-01-01"
                }
            ]
        }
    }
    return dataset


@pytest.fixture
def sensitive_dataset(sensitive_dataset_json, pas_client):
    resp = pas_client.post(
        "/v3/datasets", sensitive_dataset_json, content_type="application/json"
    )
    assert resp.status_code == 201

    return Dataset.objects.get(id=resp.data["id"])


def test_create_sensitive_dataset(sensitive_dataset_json, sensitive_contract, pas_client):
    """
    Test creating a sensitive dataset
    """
    resp = pas_client.post(
        "/v3/datasets?include_nulls=true",
        sensitive_dataset_json,
        content_type="application/json"
    )

    assert resp.status_code == 201

    data = resp.data

    assert data["data_sensitivity"]["is_sensitive"] is True
    assert len(data["data_sensitivity"]["rationales"]) == 1
    assert data["data_sensitivity"]["rationales"][0]["rationale"]["url"] \
        == sensitive_contract.rationales.first().rationale.url
    assert data["data_sensitivity"]["rationales"][0]["expiration_date"] == "2027-01-01"


def test_data_sensitive_hidden(sensitive_dataset, pas_client, ida_client, user_client):
    """
    Test that 'data_sensitivity' field is hidden for non-PAS users
    """
    dataset_id = sensitive_dataset.id
    resp = pas_client.get(f"/v3/datasets/{dataset_id}")

    # 'data_sensitivity' visible for PAS service user
    assert resp.status_code == 200
    assert "data_sensitivity" in resp.data

    for client in [ida_client, user_client]:
        # 'data_sensitivity' hidden for other users
        resp = client.get(f"/v3/datasets/{dataset_id}")
        assert resp.status_code == 200
        assert "data_sensitivity" not in resp.data
