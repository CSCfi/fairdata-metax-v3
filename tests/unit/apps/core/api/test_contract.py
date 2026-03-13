import pytest

from apps.core.factories import SensitivityRationaleFactory
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


def test_update_contract_id(admin_client, contract_a):
    contract_id = contract_a.json()["id"]
    resp = admin_client.patch(
        f"/v3/contracts/{contract_id}",
        {"id": "uusi id"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "cannot be changed for an existing contract" in resp.json()["id"]


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


def test_contract_set_sensitive_data(pas_client, contract_a):
    contract_id = contract_a.json()["id"]

    rationale = SensitivityRationaleFactory()
    rationale2 = SensitivityRationaleFactory()

    resp = pas_client.patch(
        f"/v3/contracts/{contract_id}?include_nulls=True",
        {
            "data_sensitivity": {
                "is_sensitive": True,
                "rationales": [
                    {
                        "rationale": {"url": rationale.url}
                    },
                    {
                        "rationale": {"url": rationale2.url},
                        "expiration_date": "2027-01-01"
                    }
                ]
            }
        },
        content_type="application/json"
    )

    assert resp.status_code == 200

    assert resp.data["data_sensitivity"]["is_sensitive"] is True
    assert len(resp.data["data_sensitivity"]["rationales"]) == 2
    rationales = resp.data["data_sensitivity"]["rationales"]

    assert rationales[0]["rationale"]["url"] == rationale.url
    assert rationales[0]["expiration_date"] is None

    assert rationales[1]["rationale"]["url"] == rationale2.url
    assert rationales[1]["expiration_date"] == "2027-01-01"

    resp = pas_client.patch(
        f"/v3/contracts/{contract_id}",
        {
            "data_sensitivity": {"is_sensitive": False, "rationales": []}
        },
        content_type="application/json"
    )

    assert resp.status_code == 200

    assert resp.data["data_sensitivity"]["is_sensitive"] is False
    assert not resp.data["data_sensitivity"]["rationales"]


def test_contract_hide_sensitivity_from_nonpas(pas_client, ida_client, user_client, contract_a):
    contract_id = contract_a.json()["id"]

    # 'data_sensitivity' field visible for PAS service user
    resp = pas_client.get(f"/v3/contracts/{contract_id}")
    assert "validity" in resp.data
    assert "data_sensitivity" in resp.data

    # 'data_sensitivity' hidden for other users
    for client in [ida_client, user_client]:
        resp = client.get(f"/v3/contracts/{contract_id}")
        assert "validity" in resp.data
        assert "data_sensitivity" not in resp.data
