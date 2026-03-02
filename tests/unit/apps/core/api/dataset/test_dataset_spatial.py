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


def test_create_dataset_geolocations_bulk(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiPolygon",
                            "coordinates": [
                                [
                                    [
                                        [19.0, 59.0],
                                        [20.0, 59.0],
                                        [20.0, 65.0],
                                        [19.0, 65.0],
                                        [19.0, 59.0]
                                    ]
                                ],
                                [
                                    [
                                        [21.0, 61.0],
                                        [22.0, 61.0],
                                        [22.0, 62.0],
                                        [21.0, 62.0],
                                        [21.0, 61.0]
                                    ]
                                ]
                            ]
                        }
                    }
                ]
            }
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

    assert res.data["spatial"][0]["geolocations"]["features"][0]["geometry"]["type"] == "MultiPolygon"



def test_remove_dataset_geolocations_bulk(
    admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [10.0, 50.0]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [10.5, 50.5],
                                [11.0, 51.0],
                                [11.5, 50.5]
                            ]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [12.0, 52.0],
                                    [13.0, 52.0],
                                    [13.0, 53.0],
                                    [12.0, 53.0],
                                    [12.0, 52.0]
                                ]
                            ]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [14.0, 54.0],
                                    [15.0, 54.0],
                                    [15.0, 55.0],
                                    [14.0, 55.0],
                                    [14.0, 54.0]
                                ],
                                [
                                    [14.2, 54.2],
                                    [14.8, 54.2],
                                    [14.8, 54.8],
                                    [14.2, 54.8],
                                    [14.2, 54.2]
                                ]
                            ]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiPoint",
                            "coordinates": [
                                [16.0, 56.0],
                                [16.1, 56.1]
                            ]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiLineString",
                            "coordinates": [
                                [
                                    [17.0, 57.0],
                                    [17.5, 57.5]
                                ],
                                [
                                    [18.0, 58.0],
                                    [18.5, 58.5]
                                ]
                            ]
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiPolygon",
                            "coordinates": [
                                [
                                    [
                                        [19.0, 59.0],
                                        [20.0, 59.0],
                                        [20.0, 60.0],
                                        [19.0, 60.0],
                                        [19.0, 59.0]
                                    ]
                                ],
                                [
                                    [
                                        [21.0, 61.0],
                                        [22.0, 61.0],
                                        [22.0, 62.0],
                                        [21.0, 62.0],
                                        [21.0, 61.0]
                                    ]
                                ]
                            ]
                        },
                    }
                ]
            }
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

    assert res.data["spatial"][0]["geolocations"]["features"][0]["geometry"]["type"] == "Point"
    assert len(res.data["spatial"][0]["geolocations"]["features"]) == 7

    dataset_id = res.data["id"]
    spatials[0]["geolocations"] = {}
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"spatial": spatials, "provenance": provenances},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert len(res.data["spatial"][0]["geolocations"]["features"]) == 0


def test_create_invalid_dataset_geolocations_bulk(admin_client, dataset_a_json, data_catalog, reference_data, mocker
):
    spatials = [
        {
            "geographic_name": "Alppikylä",
            "reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"},
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [12.0, 52.0],
                                    [13.0, 52.0],
                                    [13.0, 53.0],
                                    [12.0, 53.0],
                                    [12.1, 52.1]
                                ]
                            ]
                        }
                    }
                ]
            }
        },
        {
            "geographic_name": "Koitajoki",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105080"},
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [10.0, 50.0]
                        },
                    }
                ]
            }
        },
    ]
    provenances = [
        {
            "spatial": {
                "geographic_name": "Tapiola",
                "reference": {"url": "http://www.yso.fi/onto/yso/p105747"},
                "geolocations": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "MultiPoint",
                                "coordinates": [
                                    [16.0, 56.0],
                                    [16.1, 56.1]
                                ]
                            },
                        }
                    ]
                }
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
    assert res.status_code == 400

    spatials[0]["geolocations"]["features"] = [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [12.0, 52.0],
                                    [13.0, 52.0],
                                    [13.0, 53.0],
                                    [12.0, 53.0],
                                    [12.0, 52.0]
                                ]
                            ]
                        }
                    }
                ]
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

    assert res.data["spatial"][0]["geolocations"]["features"][0]["geometry"]["type"] == "Polygon"
    assert res.data["spatial"][1]["geolocations"]["features"][0]["geometry"]["type"] == "Point"
    assert res.data["provenance"][0]["spatial"]["geolocations"]["features"][0]["geometry"]["type"] == "MultiPoint"