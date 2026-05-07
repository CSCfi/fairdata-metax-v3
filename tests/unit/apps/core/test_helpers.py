import logging

import pytest
from django.contrib.gis.geos import GEOSGeometry

from apps.common.helpers import normalize_wkt
from apps.core import factories
from apps.core.helpers import fill_missing_geometry, normalize_spatial_wkts
from apps.core.models import Spatial
from apps.core.models.concepts import GeoLocation


@pytest.mark.django_db
def test_normalize_spatial_wkts():
    spatial1 = factories.SpatialFactory(custom_wkt=[" POINT   (50.0  50   ) "])
    spatial2 = factories.SpatialFactory(custom_wkt=["POINT (25 30)"])
    assert normalize_spatial_wkts(Spatial.objects.all()) == 1  # one update
    spatial1.refresh_from_db()
    assert spatial1.custom_wkt == ["POINT (50 50)"]

    spatial2.refresh_from_db()
    assert spatial2.custom_wkt == ["POINT (25 30)"]


@pytest.mark.django_db
def test_fill_missing_geometry_wkt_to_geolocations(caplog):
    logging.disable(logging.NOTSET)  # Log invalid WKT

    spatials = [
        Spatial.objects.create(custom_wkt=["POINT (65 30)", "POINT (65 35)"]),
        Spatial.objects.create(custom_wkt=[normalize_wkt("""
            GEOMETRYCOLLECTION (POINT (40 10),
            LINESTRING (10 10, 20 20, 10 40),
            POLYGON ((40 40, 20 45, 45 30, 40 40)))
        """)]),
        Spatial.objects.create(custom_wkt=["THISISINVALIDWKT (1 1)"]),
    ]

    fill_missing_geometry(Spatial.objects.all())

    geometries = []
    for spatial in spatials:
        spatial.refresh_from_db()
        geometries.append(
            [
                geometry.wkt
                for geometry in spatial.geolocations.values_list("geometry_2d", flat=True)
            ]
        )

    assert geometries == [
        ["POINT (65 30)", "POINT (65 35)"],
        [normalize_wkt("""
            GEOMETRYCOLLECTION (POINT (40 10),
            LINESTRING (10 10, 20 20, 10 40),
            POLYGON ((40 40, 20 45, 45 30, 40 40)))
        """)],
        [],  # Skipped invalid wkt
    ]

    assert len(caplog.messages) == 2
    assert "Invalid wkt" in caplog.messages[0]
    assert "geolocation_created=2" in caplog.messages[1]


@pytest.mark.django_db
def test_fill_missing_geometry_geolocations_to_wkt(caplog):
    logging.disable(logging.NOTSET)

    s1 = Spatial.objects.create()
    s1.geolocations.set(
        [
            GeoLocation.objects.create(geometry=GEOSGeometry("POINT (65 30)")),
            GeoLocation.objects.create(geometry=GEOSGeometry("POINT (65 35)")),
        ]
    )
    s2 = Spatial.objects.create()
    s2.geolocations.set(
        [
            GeoLocation.objects.create(geometry=GEOSGeometry(normalize_wkt("""
            GEOMETRYCOLLECTION (POINT (40 10),
            LINESTRING (10 10, 20 20, 10 40),
            POLYGON ((40 40, 20 45, 45 30, 40 40)))
        """))),
        ]
    )

    spatials = [s1, s2]
    fill_missing_geometry(Spatial.objects.all())

    geometries = []
    for spatial in spatials:
        spatial.refresh_from_db()
        geometries.append(spatial.custom_wkt)

    assert geometries == [
        ["POINT (65 30)", "POINT (65 35)"],
        [normalize_wkt("""
            GEOMETRYCOLLECTION (POINT (40 10),
            LINESTRING (10 10, 20 20, 10 40),
            POLYGON ((40 40, 20 45, 45 30, 40 40)))
        """)],
    ]
    assert len(caplog.messages) == 1
    assert "wkt_created=2" in caplog.messages[0]
