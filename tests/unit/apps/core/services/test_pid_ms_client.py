from apps.core.factories import DatasetFactory
from apps.core.services.pid_ms_client import _PIDMSClient as PIDMSClient


def test_create_urn(requests_mock):
    dataset = DatasetFactory()
    assert PIDMSClient().create_urn(dataset.id).startswith("urn:")
    assert requests_mock.call_count == 1
    assert requests_mock.request_history[0].method == "POST"
    assert requests_mock.request_history[0].url == "https://pidmsbaseurl/v1/pid"
    assert requests_mock.request_history[0].json() == {
        "url": f"https://etsin-test/dataset/{dataset.id}",
        "type": "URN",
        "persist": 0,
    }


def test_create_doi(admin_client, requests_mock):
    dataset = DatasetFactory()
    assert PIDMSClient().create_doi(dataset.id).startswith("10.")
    assert requests_mock.call_count == 1
    assert requests_mock.request_history[0].method == "POST"
    assert requests_mock.request_history[0].url == "https://pidmsbaseurl/v1/pid/doi"
    payload_data = requests_mock.request_history[0].json()["data"]
    assert payload_data["type"] == "dois"
    assert payload_data["attributes"]["url"] == f"https://etsin-test/dataset/{dataset.id}"
