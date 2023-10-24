import logging

import pytest
from rest_framework import serializers

from apps.core.serializers import SpatialModelSerializer

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db]

def test_create_temporal_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 201
    assert len(resp.json()["temporal"]) == 1


def test_create_temporal_dataset_fail(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["temporal"] = [
        {"start_date": "2050-01-01T09:43:48.000000Z", "end_date": "2020-11-25T09:43:48.000000Z"}
    ]
    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 400
    assert "is before start_date" in resp.json()["temporal"][0]["end_date"][0]
