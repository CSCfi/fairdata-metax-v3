import pytest

from apps.core.models import Contract

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


def test_create_contract(admin_client, contract_a_json):
    resp = admin_client.post("/v3/contracts", contract_a_json, content_type="application/json")

    assert resp.status_code == 201

    data = resp.json()
    assert data["title"]["en"] == "Test contract A"
    assert data["quota"] == 123456789


def test_update_contract(admin_client, contract_a):
    contract_id = contract_a.json()["id"]
    resp = admin_client.patch(
        f"/v3/contracts/{contract_id}",
        {"id": contract_id, "quota": 987654321},
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["title"]["en"] == "Test contract A"
    assert data["quota"] == 987654321
