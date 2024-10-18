import pytest

from apps.core.models import Contract

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


def test_create_contract(admin_client, contract_a_json):
    resp = admin_client.post("/v3/contracts", contract_a_json, content_type="application/json")

    assert resp.status_code == 201

    data = resp.json()
    assert data["title"] == {"en": "Test contract A", "fi": "Testisopimus A"}
    assert data["description"] == {
        "en": "Description for test contract A",
        "fi": "Testisopimus A:n kuvaus",
    }
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


def test_contract_permissions(user_client, pas_client, contract_a):
    contract_id = contract_a.json()["id"]

    resp = user_client.patch(
        f"/v3/contracts/{contract_id}",
        {"title": {"en": "user title"}},
        content_type="application/json",
    )
    assert resp.status_code == 403

    resp = pas_client.patch(
        f"/v3/contracts/{contract_id}",
        {"title": {"en": "pas title"}},
        content_type="application/json",
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["title"]["en"] == "pas title"


def test_contract_from_legacy(v2_migration_client, legacy_contract_json):
    """Test contracts from legacy endpoint."""
    # Create contract from legacy
    resp = v2_migration_client.post(
        "/v3/contracts/from-legacy", legacy_contract_json, content_type="application/json"
    )
    assert resp.status_code == 201
    assert resp.data["title"]["und"] == "Testisopimus"

    # Update contract from legacy
    legacy_contract_json["contract_json"]["title"] = "Uusi otsikko"
    resp = v2_migration_client.post(
        "/v3/contracts/from-legacy", legacy_contract_json, content_type="application/json"
    )
    assert resp.status_code == 200
    assert resp.data["title"]["und"] == "Uusi otsikko"

    # Make sure the changes are saved to db
    assert Contract.all_objects.count() == 1
    assert Contract.all_objects.first().title["und"] == "Uusi otsikko"


def test_contract_from_legacy_permissions(user_client, legacy_contract_json):
    resp = user_client.post(
        "/v3/contracts/from-legacy", legacy_contract_json, content_type="application/json"
    )
    assert resp.status_code == 403
