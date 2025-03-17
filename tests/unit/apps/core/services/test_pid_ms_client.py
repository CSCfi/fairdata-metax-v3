import pytest

from apps.core.factories import DatasetFactory
from apps.core.services.pid_ms_client import ServiceUnavailableError, _PIDMSClient as PIDMSClient

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("mock_pid_ms")]


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


def test_create_invalid_doi_response_status_0_body_empty(requests_mock):
    dataset = DatasetFactory()
    requests_mock.post("https://pidmsbaseurl/v1/pid/doi", text="", status_code=0)
    with pytest.raises(ServiceUnavailableError) as ec:
        PIDMSClient().create_doi(dataset.id)

    # Check the original exception that caused the ServiceUnavailableError
    assert str(ec.value.__context__) == "Invalid status code 0 in response: "


def test_create_invalid_doi_response_status_200_wrong_prefix(requests_mock):
    dataset = DatasetFactory()
    requests_mock.post("https://pidmsbaseurl/v1/pid/doi", text="notdoi", status_code=200)
    with pytest.raises(ServiceUnavailableError) as ec:
        PIDMSClient().create_doi(dataset.id)

    # Check the original exception that caused the ServiceUnavailableError
    assert "PID MS returned invalid identifier='notdoi'" in str(ec.value.__context__)


def test_create_invalid_urn_response_status_0_body_empty(requests_mock):
    dataset = DatasetFactory()
    requests_mock.post("https://pidmsbaseurl/v1/pid", text="", status_code=0)
    with pytest.raises(ServiceUnavailableError) as ec:
        PIDMSClient().create_urn(dataset.id)

    # Check the original exception that caused the ServiceUnavailableError
    assert str(ec.value.__context__) == "Invalid status code 0 in response: "


def test_create_invalid_urn_response_status_0_body_empty(requests_mock):
    dataset = DatasetFactory()
    requests_mock.post("https://pidmsbaseurl/v1/pid", text="noturn", status_code=200)
    with pytest.raises(ServiceUnavailableError) as ec:
        PIDMSClient().create_urn(dataset.id)

    # Check the original exception that caused the ServiceUnavailableError
    assert "PID MS returned invalid identifier='noturn'" in str(ec.value.__context__)
