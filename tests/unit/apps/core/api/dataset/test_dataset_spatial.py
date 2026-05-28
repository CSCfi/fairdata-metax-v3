import logging

import pytest
from apps.core.factories import LocationFactory
from apps.core.models.catalog_record.dataset import Dataset
import shapely
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
                                        [19.0, 59.0],
                                    ]
                                ],
                                [
                                    [
                                        [21.0, 61.0],
                                        [22.0, 61.0],
                                        [22.0, 62.0],
                                        [21.0, 62.0],
                                        [21.0, 61.0],
                                    ]
                                ],
                            ],
                        },
                    }
                ],
            },
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

    assert (
        res.data["spatial"][0]["geolocations"]["features"][0]["geometry"]["type"] == "MultiPolygon"
    )


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
                        "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[10.5, 50.5], [11.0, 51.0], [11.5, 50.5]],
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
                                    [12.0, 52.0],
                                ]
                            ],
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
                                    [14.0, 54.0],
                                ],
                                [
                                    [14.2, 54.2],
                                    [14.8, 54.2],
                                    [14.8, 54.8],
                                    [14.2, 54.8],
                                    [14.2, 54.2],
                                ],
                            ],
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiPoint",
                            "coordinates": [[16.0, 56.0], [16.1, 56.1]],
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "MultiLineString",
                            "coordinates": [
                                [[17.0, 57.0], [17.5, 57.5]],
                                [[18.0, 58.0], [18.5, 58.5]],
                            ],
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
                                        [19.0, 59.0],
                                    ]
                                ],
                                [
                                    [
                                        [21.0, 61.0],
                                        [22.0, 61.0],
                                        [22.0, 62.0],
                                        [21.0, 62.0],
                                        [21.0, 61.0],
                                    ]
                                ],
                            ],
                        },
                    },
                ],
            },
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

    # Clear geolocations
    dataset_id = res.data["id"]
    spatials[0]["geolocations"] = None
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"spatial": spatials, "provenance": provenances},
        content_type="application/json",
    )
    assert res.status_code == 200, res.data
    assert "geolocations" not in res.data["spatial"][0]


def test_create_invalid_dataset_geolocations_bulk(
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
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [12.0, 52.0],
                                    [13.0, 52.0],
                                    [13.0, 53.0],
                                    [12.0, 53.0],
                                    [12.1, 52.1],
                                ]
                            ],
                        },
                    }
                ],
            },
        },
        {
            "geographic_name": "Koitajoki",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105080"},
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
                    }
                ],
            },
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
                                "coordinates": [[16.0, 56.0], [16.1, 56.1]],
                            },
                        }
                    ],
                },
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
                    [[12.0, 52.0], [13.0, 52.0], [13.0, 53.0], [12.0, 53.0], [12.0, 52.0]]
                ],
            },
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
    assert (
        res.data["provenance"][0]["spatial"]["geolocations"]["features"][0]["geometry"]["type"]
        == "MultiPoint"
    )


def test_create_dataset_geolocations_copy(
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
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [19.0, 59.0],
                                    [20.0, 59.0],
                                    [20.0, 65.0],
                                    [19.0, 65.0],
                                    [19.0, 59.0],
                                ]
                            ],
                        },
                    }
                ],
            },
        },
    ]
    res = admin_client.post(
        "/v3/datasets",
        {**dataset_a_json, "spatial": spatials},
        content_type="application/json",
    )
    assert res.status_code == 201
    dataset_id = res.data["id"]

    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/new-version", content_type="application/json"
    )
    assert res.status_code == 201

    res = admin_client.get("/v3/datasets")
    assert res.data["count"] == 2
    d1 = res.data["results"][0]
    d2 = res.data["results"][1]
    assert len(d1["spatial"][0]["geolocations"]["features"]) == 1
    assert len(d2["spatial"][0]["geolocations"]["features"]) == 1


def test_dataset_spatial_validate_features(
    admin_client, dataset_minimal_draft_json, data_catalog, reference_data, mocker
):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [{"geolocations": {"type": "jeejee"}}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 400, res.data
    assert "not a valid choice" in res.json()["spatial"][0]["geolocations"]["type"][0]
    assert "field is required" in res.json()["spatial"][0]["geolocations"]["features"][0]

    dataset_json["spatial"] = [{"geolocations": {"type": "FeatureCollection", "features": []}}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 400, res.data
    assert (
        "Ensure this field has at least 1"
        in res.json()["spatial"][0]["geolocations"]["features"]["non_field_errors"][0]
    )


def test_dataset_spatial_validate_geometry(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    geometry = {"type": "Poing", "coordinates": [61, 24]}
    dataset_json["spatial"] = [
        {
            "geolocations": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": geometry}],
            }
        }
    ]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 400, res.data
    assert (
        res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"][0]
        == "Unknown geometry type"
    )


def test_dataset_spatial_validate_properties(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    geometry = {"type": "Point", "coordinates": [61, 24]}
    dataset_json["spatial"] = [
        {
            "geolocations": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": geometry, "properties": "someprop"}],
            }
        }
    ]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 400, res.data
    assert (
        "must be a dict"
        in res.json()["spatial"][0]["geolocations"]["features"][0]["properties"][0]
    )


def test_dataset_spatial_3d_geometry_geolocation(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    geometry = {"type": "Point", "coordinates": [61, 24, 100]}
    dataset_json["spatial"] = [
        {
            "geolocations": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": geometry}],
            }
        }
    ]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    loc = dataset.spatial.first().geolocations.first()
    assert loc.geometry_3d.geom_type == "Point"
    assert loc.geometry_3d.coords == (61.0, 24.0, 100.0)
    assert loc.geometry_2d.geom_type == "Point"
    assert loc.geometry_2d.coords == (61.0, 24.0)


def test_dataset_spatial_properties(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [
        {
            "geolocations": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [61, 24]},
                        "properties": {
                            "this": "is",
                            "a": "json object",
                            "value": 1,
                            "subobject": {"works": "ok"},
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [12, 34]},
                        "properties": {
                            "another": "feature",
                        },
                    },
                ],
            }
        }
    ]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201, res.data
    assert res.data["spatial"][0]["geolocations"]["features"][0]["properties"] == {
        "this": "is",
        "a": "json object",
        "value": 1,
        "subobject": {"works": "ok"},
    }
    assert res.data["spatial"][0]["geolocations"]["features"][1]["properties"] == {
        "another": "feature"
    }


def test_dataset_spatial_3d_geometry_wkt(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [{"custom_wkt": ["POINT(61 24 100)"]}]

    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    loc = dataset.spatial.first().geolocations.first()
    assert loc.geometry_3d.geom_type == "Point"
    assert loc.geometry_3d.coords == (61.0, 24.0, 100.0)
    assert loc.geometry_2d.geom_type == "Point"
    assert loc.geometry_2d.coords == (61.0, 24.0)


def test_dataset_spatial_wkt_geolocation(
    admin_client, dataset_minimal_draft_json, subtests: pytest.Subtests
):
    dataset_json = dataset_minimal_draft_json

    geolocation = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [61.1, 24.9]}}
        ],
    }
    wkt = ["POINT (61.1 24.9)"]
    wkt2 = ["POINT (61.1000001 24.9)"]

    with subtests.test("gelocation -> wkt"):
        dataset_json["spatial"] = [{"geolocations": geolocation}]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.data
        assert res.data["spatial"][0]["custom_wkt"] == wkt

    with subtests.test("wkt -> geolocation"):
        dataset_json["spatial"] = [{"custom_wkt": wkt}]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.data
        assert (
            res.data["spatial"][0]["geolocations"]["features"][0]["geometry"]
            == geolocation["features"][0]["geometry"]
        )

    with subtests.test("wkt + geolocation ok"):
        dataset_json["spatial"] = [{"custom_wkt": wkt, "geolocations": geolocation}]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.data

    with subtests.test("wkt + geolocation mismatch"):
        dataset_json["spatial"] = [{"custom_wkt": wkt2, "geolocations": geolocation}]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 400, res.data
        assert "both should have exactly the same geometry" in res.data["spatial"][0]["custom_wkt"]


def test_dataset_spatial_wkt_antipodal(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    wkt = "POLYGON ((-180 -90, -180 90, 180 90, 180 -90, -180 -90))"
    dataset_json["spatial"] = [{"custom_wkt": [wkt]}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201

    # Long edges in polygon should be split into smaller parts
    fixed_wkt = shapely.from_wkt(res.data["spatial"][0]["custom_wkt"][0])
    assert len(fixed_wkt.exterior.coords) > 5


@pytest.mark.parametrize(
    "wkt, ok",
    [
        ["POLYGON ((0 0, 180 0, 180 90, 0 90, 0 0))", True],
        ["POLYGON ((0 0, 181 0, 181 90, 0 90, 0 0))", False],
        ["POLYGON ((0 0, 180 0, 180 91, 0 91, 0 0))", False],
    ],
)
def test_dataset_spatial_wkt_validate_coords(wkt, ok, admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [{"custom_wkt": [wkt]}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    if ok:
        assert res.status_code == 201
    else:
        assert res.status_code == 400
        assert "should be in range" in res.json()["spatial"][0]["custom_wkt"]["0"][0]


@pytest.mark.parametrize(
    "geometry, ok",
    [
        [
            {"type": "Polygon", "coordinates": [[[0, 0], [180, 0], [180, 90], [0, 90], [0, 0]]]},
            True,
        ],
        [
            {"type": "Polygon", "coordinates": [[[0, 0], [280, 0], [180, 90], [0, 90], [0, 0]]]},
            False,
        ],
    ],
)
def test_dataset_spatial_geojson_validate_coords(
    geometry, ok, admin_client, dataset_minimal_draft_json
):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [
        {
            "geolocations": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": geometry}],
            }
        }
    ]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    if ok:
        assert res.status_code == 201, res.data
    else:
        assert res.status_code == 400
        assert (
            "should be in range"
            in res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"][0]
        )


def test_dataset_spatial_wkt_m_coordinate(admin_client, dataset_minimal_draft_json):
    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [{"custom_wkt": ["POINT M (1 2 3)"]}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 400
    assert (
        "M coordinate values are not supported" in res.json()["spatial"][0]["custom_wkt"]["0"][0]
    )


def test_dataset_geometry_from_reference(admin_client, dataset_minimal_draft_json):
    LocationFactory(
        url="http://www.yso.fi/onto/onto/yso/123",
        pref_label={"fi": "Paikka)"},
        as_wkt="POINT (60 25)",
    )

    dataset_json = dataset_minimal_draft_json
    dataset_json["spatial"] = [{"reference": {"url": "http://www.yso.fi/onto/onto/yso/123"}}]
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201
    geom = res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"]
    assert geom["type"] == "Point"
    assert geom["coordinates"] == [60, 25]


def test_dataset_geometry_from_reference_and_geolocation(admin_client, dataset_minimal_draft_json, subtests):
    LocationFactory(
        url="http://www.yso.fi/onto/onto/yso/123",
        pref_label={"fi": "Paikka)"},
        as_wkt="POINT (60 25)",
    )
    dataset_json = dataset_minimal_draft_json

    with subtests.test("reference wkt and geolocations match -> no custom wkt"):
        dataset_json["spatial"] = [
            {
                "reference": {"url": "http://www.yso.fi/onto/onto/yso/123"},
                "geolocations": {
                    "type": "FeatureCollection",
                    "features": [
                        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [60, 25]}}
                    ],
                },
            }
        ]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.json()
        geom = res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"]
        assert geom["type"] == "Point"
        assert geom["coordinates"] == [60, 25]
        assert res.json()["spatial"][0]["custom_wkt"] == []

    with subtests.test("reference wkt and geolocations don't match -> convert to custom wkt"):
        dataset_json["spatial"][0]["geolocations"]["features"][0]["geometry"]["coordinates"] = [60.1, 25]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.json()
        geom = res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"]
        assert geom["type"] == "Point"
        assert geom["coordinates"] == [60.1, 25]
        assert res.json()["spatial"][0]["custom_wkt"] == ["POINT (60.1 25)"]

    with subtests.test("no reference wkt -> convert to custom wkt"):
        del dataset_json["spatial"][0]["reference"]
        dataset_json["spatial"][0]["geolocations"]["features"][0]["geometry"]["coordinates"] = [60, 25]
        res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
        assert res.status_code == 201, res.json()
        geom = res.json()["spatial"][0]["geolocations"]["features"][0]["geometry"]
        assert geom["type"] == "Point"
        assert geom["coordinates"] == [60, 25]
        assert res.json()["spatial"][0]["custom_wkt"] == ["POINT (60 25)"]