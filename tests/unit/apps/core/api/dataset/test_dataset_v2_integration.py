import logging
import re

import pytest

from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert Dataset.all_objects.count() == 1


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_fail(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=400)
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 409
    assert Dataset.all_objects.count() == 0
