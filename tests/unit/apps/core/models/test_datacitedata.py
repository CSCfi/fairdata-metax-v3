import pytest

from apps.common.datacitedata import Datacitedata
from shapely.geometry import (
    GeometryCollection,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    MultiLineString,
    LineString,
)

from apps.core import factories
from apps.core.models.concepts import Spatial


def test_flatten_geometry():
    """Flattened geometry should contain only primitive shapes."""
    geometry = GeometryCollection(
        [
            Point([10, 10]),
            MultiPoint([Point([20, 20]), Point([30, 30])]),
            Polygon([[0, -2], [1, -2], [1, -1], [0, -1], [0, -2]]),
            MultiPolygon(
                [
                    Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]),
                    Polygon([[0, 2], [1, 2], [1, 3], [0, 3], [0, 2]]),
                ]
            ),
            LineString([[100, 0], [200, 0], [300, 0]]),
            MultiLineString(
                [
                    LineString([[100, 10], [200, 10], [300, 10]]),
                    LineString([[100, 20], [200, 20], [300, 20]]),
                ]
            ),
            GeometryCollection(
                [
                    Point([1000, 1000]),
                    Polygon([[1000, 1000], [2000, 1000], [1000, 2000], [1000, 1000]]),
                ]
            ),
        ]
    )
    flat = Datacitedata().flatten_geometry(geometry)
    assert flat == [
        Point([10, 10]),
        Point([20, 20]),
        Point([30, 30]),
        Polygon([[0, -2], [1, -2], [1, -1], [0, -1], [0, -2]]),
        Polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]),
        Polygon([[0, 2], [1, 2], [1, 3], [0, 3], [0, 2]]),
        LineString([[100, 0], [200, 0], [300, 0]]),
        LineString([[100, 10], [200, 10], [300, 10]]),
        LineString([[100, 20], [200, 20], [300, 20]]),
        Point([1000, 1000]),
        Polygon([[1000, 1000], [2000, 1000], [1000, 2000], [1000, 1000]]),
    ]


@pytest.mark.parametrize(
    "wkt, is_ok",
    [
        ["POINT(0 10)", True],
        ["POINT(180 90)", True],
        ["POINT(-180 -90)", True],
        ["POINT(181 0)", False],
        ["POINT(-181 0)", False],
        ["POINT(0 91)", False],
        ["POINT(0 -91)", False],
    ],
)
def test_validate_geolocations_point(wkt, is_ok):
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(Spatial(custom_wkt=[wkt]))
    if is_ok:
        assert len(locations) == 1
        assert locations[0].get("geoLocationPoint") is not None
    else:
        assert len(locations) == 0


@pytest.mark.parametrize(
    "wkt, is_ok",
    [
        ["POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))", True],
        ["POLYGON ((30 10, 40 40, 20 40, 1234 20, 30 10))", False],  # Invalid longitude
        ["POLYGON ((30 10, 40 40, 20 40, 10 20))", False],  # Loop not closed
    ],
)
def test_validate_geolocations_polygon(wkt, is_ok):
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(Spatial(custom_wkt=[wkt]))
    if is_ok:
        assert len(locations) == 1
        assert len(locations[0].get("geoLocationPolygons")) == 1
    else:
        assert len(locations) == 0


def test_get_geolocations_linestring():
    """LineString is not supported in datacite, so produces no geolocation."""
    wkt = "LINESTRING (0 0, 0 10, 10 0, 0 0)"
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(Spatial(wkt))
    assert len(locations) == 0


def test_get_geolocations_multiple_polygons():
    """Single spatial with multiple polygons should produce one geolocation."""
    wkt1 = "POLYGON ((0 0, 0 10, 10 0, 0 0))"
    wkt2 = "POLYGON ((0 20, 20 20, 0 40, 0 20))"
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(Spatial(custom_wkt=[wkt1, wkt2]))
    assert len(locations) == 1
    assert len(locations[0]["geoLocationPolygons"]) == 2
    assert locations[0] == {
        "geoLocationPolygons": [
            {
                "polygonPoints": [
                    {"pointLongitude": "0.0", "pointLatitude": "0.0"},
                    {"pointLongitude": "0.0", "pointLatitude": "10.0"},
                    {"pointLongitude": "10.0", "pointLatitude": "0.0"},
                    {"pointLongitude": "0.0", "pointLatitude": "0.0"},
                ]
            },
            {
                "polygonPoints": [
                    {"pointLongitude": "0.0", "pointLatitude": "20.0"},
                    {"pointLongitude": "20.0", "pointLatitude": "20.0"},
                    {"pointLongitude": "0.0", "pointLatitude": "40.0"},
                    {"pointLongitude": "0.0", "pointLatitude": "20.0"},
                ]
            },
        ]
    }


def test_get_geolocations_multipolygon():
    """Single spatial with multipolygon should produce one geolocation."""
    wkt = "MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)), ((15 5, 40 10, 10 20, 5 10, 15 5)))"
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(Spatial(custom_wkt=[wkt]))
    assert len(locations) == 1
    assert locations[0] == {
        "geoLocationPolygons": [
            {
                "polygonPoints": [
                    {"pointLatitude": "20.0", "pointLongitude": "30.0"},
                    {"pointLatitude": "40.0", "pointLongitude": "45.0"},
                    {"pointLatitude": "40.0", "pointLongitude": "10.0"},
                    {"pointLatitude": "20.0", "pointLongitude": "30.0"},
                ]
            },
            {
                "polygonPoints": [
                    {"pointLatitude": "5.0", "pointLongitude": "15.0"},
                    {"pointLatitude": "10.0", "pointLongitude": "40.0"},
                    {"pointLatitude": "20.0", "pointLongitude": "10.0"},
                    {"pointLatitude": "10.0", "pointLongitude": "5.0"},
                    {"pointLatitude": "5.0", "pointLongitude": "15.0"},
                ]
            },
        ]
    }


def test_get_geolocations_collection_multipoint():
    """Collection with multiple points (or multipoint) should produce multiple locations."""
    wkt = """GEOMETRYCOLLECTION (
        POINT (0 0),
        MULTIPOINT (0 10, 0 20, 0 30),
        POLYGON ((40 40, 20 45, 45 30, 40 40)),
        POLYGON ((0 70, 100 70, 0 80, 0 70))
    )"""
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(
        Spatial(geographic_name="Some location", custom_wkt=[wkt])
    )

    # Geolocation can have only one point but multiple polygons.
    # Create a location for all polygons and a location for each point.
    assert len(locations) == 5
    assert locations == [
        {
            "geoLocationPlace": "Some location",
            "geoLocationPolygons": [
                {
                    "polygonPoints": [
                        {"pointLongitude": "40.0", "pointLatitude": "40.0"},
                        {"pointLongitude": "20.0", "pointLatitude": "45.0"},
                        {"pointLongitude": "45.0", "pointLatitude": "30.0"},
                        {"pointLongitude": "40.0", "pointLatitude": "40.0"},
                    ]
                },
                {
                    "polygonPoints": [
                        {"pointLongitude": "0.0", "pointLatitude": "70.0"},
                        {"pointLongitude": "100.0", "pointLatitude": "70.0"},
                        {"pointLongitude": "0.0", "pointLatitude": "80.0"},
                        {"pointLongitude": "0.0", "pointLatitude": "70.0"},
                    ]
                },
            ],
        },
        {
            "geoLocationPlace": "Some location",
            "geoLocationPoint": {"pointLongitude": "0.0", "pointLatitude": "0.0"},
        },
        {
            "geoLocationPlace": "Some location",
            "geoLocationPoint": {"pointLongitude": "0.0", "pointLatitude": "10.0"},
        },
        {
            "geoLocationPlace": "Some location",
            "geoLocationPoint": {"pointLongitude": "0.0", "pointLatitude": "20.0"},
        },
        {
            "geoLocationPlace": "Some location",
            "geoLocationPoint": {"pointLongitude": "0.0", "pointLatitude": "30.0"},
        },
    ]


def test_get_geolocations_collection_single_point():
    """Collection with single point produce single location."""
    wkt = """GEOMETRYCOLLECTION (
        POINT (0 0),
        POLYGON ((40 40, 20 45, 45 30, 40 40)),
        POLYGON ((0 70, 100 70, 0 80, 0 70))
    )"""
    dd = Datacitedata()
    locations = dd.get_spatial_geolocations(
        Spatial(geographic_name="Some location", custom_wkt=[wkt])
    )

    # A geolocation can have a single point and multiple polygons, create only one location.
    assert len(locations) == 1
    assert locations == [
        {
            "geoLocationPlace": "Some location",
            "geoLocationPoint": {"pointLongitude": "0.0", "pointLatitude": "0.0"},
            "geoLocationPolygons": [
                {
                    "polygonPoints": [
                        {"pointLongitude": "40.0", "pointLatitude": "40.0"},
                        {"pointLongitude": "20.0", "pointLatitude": "45.0"},
                        {"pointLongitude": "45.0", "pointLatitude": "30.0"},
                        {"pointLongitude": "40.0", "pointLatitude": "40.0"},
                    ]
                },
                {
                    "polygonPoints": [
                        {"pointLongitude": "0.0", "pointLatitude": "70.0"},
                        {"pointLongitude": "100.0", "pointLatitude": "70.0"},
                        {"pointLongitude": "0.0", "pointLatitude": "80.0"},
                        {"pointLongitude": "0.0", "pointLatitude": "70.0"},
                    ]
                },
            ],
        }
    ]


def test_get_geolocations_point_and_reference():
    """LineString is not supported in datacite, so produces no geolocation."""
    wkt = "POINT (50 50)"
    dd = Datacitedata()

    spatial = Spatial(
        custom_wkt=[wkt],
        reference=factories.LocationFactory.build(
            pref_label={"fi": "Joku paikka"}, as_wkt="POINT (90 90)"
        ),
    )

    # When custom_wkt and reference exist, use custom_wkt
    locations = dd.get_spatial_geolocations(spatial)
    assert len(locations) == 1
    assert locations[0]["geoLocationPoint"] == {"pointLatitude": "50.0", "pointLongitude": "50.0"}

    # Without custom_wkt, use reference data wkt
    spatial.custom_wkt = []
    locations = dd.get_spatial_geolocations(spatial)
    assert len(locations) == 1
    assert locations[0]["geoLocationPoint"] == {"pointLatitude": "90.0", "pointLongitude": "90.0"}

    # No wkt at all and no geographic_name, return no location
    spatial.reference = None
    locations = dd.get_spatial_geolocations(spatial)
    assert len(locations) == 0
