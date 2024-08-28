import logging

import pytest
from watson.models import SearchEntry
from watson.search import search_context_manager

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.dataset, pytest.mark.django_db]


def test_dataset_indexing(dataset_a_json, data_catalog, reference_data, admin_client):
    """Ensure dataset that fails publish validation does not create a SearchEntry."""
    # Open search context so the request behaves like when watson middleware is enabled.
    # The context is closed automatically after the next request.
    search_context_manager.start()
    dataset_license = dataset_a_json["access_rights"].pop("license")
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert SearchEntry.objects.count() == 0

    search_context_manager.start()
    dataset_a_json["access_rights"]["license"] = dataset_license
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert SearchEntry.objects.count() == 1
