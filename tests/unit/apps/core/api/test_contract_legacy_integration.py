import pytest
from tests.utils import matchers

from apps.core.models import Contract

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


class V2SyncMock:
    next_id = 1

    def callback(self, request, context):
        contracts = request.json()
        output = []
        for contract in contracts:
            out_contract = {
                "id": contract.get("id"),
                "contract_json": {"identifier": contract["contract_json"]["identifier"]},
            }
            if out_contract["id"] is None:
                out_contract["id"] = self.next_id
                self.next_id += 1
            output.append(out_contract)

        context.status_code = 200
        return output


@pytest.fixture
def mock_v2_contracts_integration(requests_mock, v2_integration_settings):
    host = v2_integration_settings.METAX_V2_HOST
    syncmock = V2SyncMock()
    return requests_mock.post(f"{host}/rest/v2/contracts/sync_from_v3", json=syncmock.callback)


def test_create_contract_integration(admin_client, contract_a_json, mock_v2_contracts_integration):
    resp = admin_client.post("/v3/contracts", contract_a_json, content_type="application/json")
    assert resp.status_code == 201

    assert mock_v2_contracts_integration.call_count == 1
    data = mock_v2_contracts_integration.request_history[0].json()[0]
    assert data["contract_json"]["title"] == "Test contract A"
    assert data["contract_json"]["description"] == "Description for test contract A"
    assert data["contract_json"]["quota"] == 123456789
    assert data["contract_json"]["identifier"] == contract_a_json["id"]
    contract = Contract.objects.get(id=contract_a_json["id"])
    assert contract.legacy_id == 1


def test_update_contract_integration(admin_client, contract_a, mock_v2_contracts_integration):
    contract_id = contract_a.json()["id"]
    resp = admin_client.patch(
        f"/v3/contracts/{contract_id}",
        {"id": contract_id, "title": {"en": "New contract title"}, "quota": 987654321},
        content_type="application/json",
    )
    assert resp.status_code == 200

    assert mock_v2_contracts_integration.call_count == 1
    data = mock_v2_contracts_integration.request_history[0].json()[0]
    assert data["contract_json"]["title"] == "New contract title"
    assert data["contract_json"]["description"] == "Description for test contract A"
    assert data["contract_json"]["quota"] == 987654321
    contract = Contract.objects.get(id=contract_a.data["id"])
    assert contract.legacy_id == 1


def test_delete_contract_integration(admin_client, contract_a, mock_v2_contracts_integration):
    contract_id = contract_a.json()["id"]
    resp = admin_client.delete(f"/v3/contracts/{contract_id}")
    assert resp.status_code == 204

    assert mock_v2_contracts_integration.call_count == 1
    data = mock_v2_contracts_integration.request_history[0].json()[0]
    assert data["contract_json"]["title"] == "Test contract A"
    assert data["removed"] == True
    assert data["date_removed"] == matchers.DateTimeStr()
    contract = Contract.all_objects.get(id=contract_a.data["id"])
    assert contract.legacy_id == 1
