import logging

import pytest

from apps.core.models import Temporal

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db]


def test_create_temporal_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 201
    assert len(resp.json()["temporal"]) == 1


def test_create_temporal_dataset_with_temporal_coverage(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    dataset_a_json["temporal"] = [
        {"temporal_coverage": "silloin tällöin"},
    ]

    # Check temporal objects are bulk created at once
    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 201
    assert len(resp.json()["temporal"]) == 1
    assert Temporal.all_objects.count() == 1


def test_create_temporal_dataset_with_provenance_temporals(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    dataset_a_json["temporal"] = [
        {"temporal_coverage": "silloin tällöin"},
    ]
    dataset_a_json["provenance"] = [
        {"temporal": {"temporal_coverage": "toisinaan"}},
        {"temporal": {"temporal_coverage": "eilen"}},
    ]

    # Check temporal objects are bulk created
    create = mocker.spy(Temporal.objects, "create")
    bulk_create = mocker.spy(Temporal.objects, "bulk_create")

    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["temporal"]) == 1
    assert len(data["provenance"]) == 2
    assert data["provenance"][0]["temporal"] == {"temporal_coverage": "toisinaan"}
    assert data["provenance"][1]["temporal"] == {"temporal_coverage": "eilen"}

    assert create.call_count == 0
    assert bulk_create.call_count == 2  # Temporal and provenance.temporal are updated separately
    assert Temporal.all_objects.count() == 3


def test_create_temporal_dataset_fail(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["temporal"] = [{"start_date": "2050-01-01", "end_date": "2020-11-25"}]
    resp = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert resp.status_code == 400
    assert "is before start_date" in resp.json()["temporal"][0]["end_date"][0]
