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


def test_data_sensitive_writable_only_by_pas(sensitive_dataset, pas_client, ida_client):
    """
    Test that 'data_sensitivity' field is only writably by PAS user
    """
    dataset_id = sensitive_dataset.id
    resp = pas_client.patch(
        f"/v3/datasets/{dataset_id}",
        {
            "data_sensitivity": {
                "is_sensitive": False,
                "rationales": []
            }
        },
        content_type="application/json"
    )

    assert resp.status_code == 200

    # Forbidden for non-PAS user
    for value in [True, False]:
        resp = ida_client.patch(
            f"/v3/datasets/{dataset_id}",
            {
                "data_sensitivity": {
                    "is_sensitive": value,
                    "rationales": []
                }
            },
            content_type="application/json"
        )

        assert resp.status_code == 400
        assert resp.data["is_sensitive"] == "Only PAS users are allowed to set is_sensitive"


def test_contract_must_be_sensitive(sensitive_contract, sensitive_dataset, pas_client):
    """
    Test that dataset cannot be made sensitive if the contract is not sensitive
    """
    resp = pas_client.patch(
        f"/v3/datasets/{sensitive_dataset.id}",
        {"data_sensitivity": {"is_sensitive": False, "rationales": []}},
        content_type="application/json"
    )
    assert resp.status_code == 200
    resp = pas_client.patch(
        f"/v3/contracts/{sensitive_contract.id}",
        {
            "data_sensitivity": {"is_sensitive": False, "rationales": []}
        },
        content_type="application/json"
    )
    assert resp.status_code == 200

    # Dataset cannot be made sensitive
    resp = pas_client.patch(
        f"/v3/datasets/{sensitive_dataset.id}",
        {
            "data_sensitivity": {"is_sensitive": True, "rationales": []}
        },
        content_type="application/json"
    )

    assert resp.status_code == 400
    assert resp.data["is_sensitive"] == "Linked contract must have 'is_sensitive' set"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_new_dataset_must_contain_rationales(sensitive_contract, dataset_a_json, pas_client):
    """
    Test that newly created must only use rationales from the linked
    contract
    """
    new_rationale = SensitivityRationaleFactory()

    resp = pas_client.post(
        "/v3/datasets",
        {
            **dataset_a_json,
            "preservation": {"contract": sensitive_contract.id},
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": new_rationale.url}}
                ]
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.data["rationales"] == \
        f"Following rationales are not listed in the linked contract: {new_rationale.url}"


def test_contract_must_contain_rationales(sensitive_contract, sensitive_dataset, pas_client):
    """
    Test that any rationales (refdata.SensitivityRationale) included
    in the dataset must also exist in the contract
    """
    sensitive_dataset.rationales.first().delete()

    # Contract will have A, B.
    # We will attempt to enter B, C into dataset.
    # C missing from contract causes an error.
    rationale_a = SensitivityRationaleFactory()
    rationale_b = SensitivityRationaleFactory()
    rationale_c = SensitivityRationaleFactory()

    resp = pas_client.patch(
        f"/v3/contracts/{sensitive_contract.id}",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": rationale_a.url}},
                    {"rationale": {"url": rationale_b.url}}
                ],
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 200

    # Attempt adding B, C into dataset.
    # A missing is allowed, but C is not allowed because it's not in the contract;
    # rationales in dataset must be a subset of contract's.
    resp = pas_client.patch(
        f"/v3/datasets/{sensitive_dataset.id}",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": rationale_b.url}},
                    {"rationale": {"url": rationale_c.url}},
                ]
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.data["rationales"] == \
        f"Following rationales are not listed in the linked contract: {rationale_c.url}"


def test_contract_must_retain_rationales(sensitive_contract, sensitive_dataset, pas_client):
    """
    Test that creating datasets using certain rationales prevents their
    removal from the contract
    """
    # Delete existing rationale
    sensitive_dataset.rationales.first().delete()

    # Contract will have A, B, C, dataset will have A, B.
    # Attempting to set contract's rationales to just B will cause an error
    # due to dataset still using rationale A.
    rationale_a = SensitivityRationaleFactory()
    rationale_b = SensitivityRationaleFactory()
    rationale_c = SensitivityRationaleFactory()

    resp = pas_client.patch(
        f"/v3/contracts/{sensitive_contract.id}",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": rationale_a.url}},
                    {"rationale": {"url": rationale_b.url}},
                    {"rationale": {"url": rationale_c.url}},
                ],
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 200

    resp = pas_client.patch(
        f"/v3/datasets/{sensitive_dataset.id}",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": rationale_a.url}},
                    {"rationale": {"url": rationale_b.url}},
                ]
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 200

    # Attempt removal of A and C from contract.
    resp = pas_client.patch(
        f"/v3/contracts/{sensitive_contract.id}",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {"rationale": {"url": rationale_b.url}}
                ]
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.data["rationales"] \
        == f"Following datasets still use rationales that are being removed: {sensitive_dataset.id}"


def test_sensitive_dataset_prevents_contract_change(sensitive_contract, sensitive_dataset, pas_client):
    """
    Test that an existing sensitive dataset prevents making the contract non-sensitive
    """
    assert sensitive_dataset.is_sensitive

    resp = pas_client.patch(
        f"/v3/contracts/{sensitive_contract.id}",
        {
            "data_sensitivity": {
                "is_sensitive": False,
                "rationales": [
                    {"rationale": {"url": sensitive_contract.rationales.first().rationale.url}}
                ]
            }
        },
        content_type="application/json"
    )
    assert resp.status_code == 400
    assert resp.data["is_sensitive"] == \
        f"Following datasets are still sensitive: {sensitive_dataset.id}"
