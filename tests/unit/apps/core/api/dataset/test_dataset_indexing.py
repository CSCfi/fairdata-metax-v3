import logging

import pytest
from watson.models import SearchEntry
from watson.search import search_context_manager

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.dataset]


@pytest.mark.django_db(transaction=True)
def test_dataset_indexing(
    dataset_a_json,
    data_catalog,
    reference_data,
    live_server,
    requests_client,
    service_user,
    update_request_client_auth_token,
):
    """Ensure dataset that fails publish validation does not create a SearchEntry."""
    update_request_client_auth_token(requests_client, service_user.token)

    dataset_license = dataset_a_json["access_rights"].pop("license")
    search_context_manager.start()  # emulate watson middleware
    res = requests_client.post(f"{live_server.url}/v3/datasets", json=dataset_a_json)
    assert res.status_code == 400
    search_context_manager.end()
    assert SearchEntry.objects.count() == 0

    dataset_a_json["access_rights"]["license"] = dataset_license
    search_context_manager.start()
    res = requests_client.post(f"{live_server.url}/v3/datasets", json=dataset_a_json)
    assert res.status_code == 201
    search_context_manager.end()
    assert SearchEntry.objects.count() == 1
