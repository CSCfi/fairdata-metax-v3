import logging

import pytest
from tests.utils import assert_nested_subdict

from apps.core.models.concepts import Spatial

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset_spatials_bulk(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
        },
        {
            "geographic_name": "Koitajoki",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105080"},
        },
    ]
    provenances = [
        {
            "spatial": {
                "geographic_name": "Tapiola",
                "reference": {"url": "http://www.yso.fi/onto/yso/p105747"},
            },
        }
    ]

    create = mocker.spy(Spatial.objects, "create")
    bulk_create = mocker.spy(Spatial.objects, "bulk_create")
    res = admin_client.post(
        "/v3/datasets",
        {**dataset_a_json, "spatial": spatials, "provenance": provenances},
        content_type="application/json",
    )
    assert res.status_code == 201
    assert_nested_subdict(spatials, res.data["spatial"])
    assert_nested_subdict(provenances, res.data["provenance"])

    # Check bulk create has been used
    assert create.call_count == 0
    assert bulk_create.call_count == 2
    assert bulk_create.mock_calls[0].args[0][0].reference.pref_label["fi"] == "Tapiola (Espoo)"
    assert (
        bulk_create.mock_calls[1].args[0][0].reference.pref_label["fi"] == "Alppikylä (Helsinki)"
    )
    assert bulk_create.mock_calls[1].args[0][1].reference.pref_label["fi"] == "Koitajoki"


def test_patch_dataset_spatials_bulk(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
        },
        {
            "geographic_name": "Koitajoki",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105080"},
        },
    ]
    provenances = [
        {
            "spatial": {
                "geographic_name": "Tapiola",
                "reference": {"url": "http://www.yso.fi/onto/yso/p105747"},
            },
        }
    ]

    create = mocker.spy(Spatial.objects, "create")
    bulk_create = mocker.spy(Spatial.objects, "bulk_create")

    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"spatial": spatials, "provenance": provenances},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict(spatials, res.data["spatial"])
    assert_nested_subdict(provenances, res.data["provenance"])

    # Check bulk create has been used
    assert create.call_count == 0
    assert bulk_create.call_count == 2
    assert bulk_create.mock_calls[0].args[0][0].reference.pref_label["fi"] == "Tapiola (Espoo)"
    assert (
        bulk_create.mock_calls[1].args[0][0].reference.pref_label["fi"] == "Alppikylä (Helsinki)"
    )
    assert bulk_create.mock_calls[1].args[0][1].reference.pref_label["fi"] == "Koitajoki"
