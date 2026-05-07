import json
from django.core.management import call_command
from django.contrib.gis.geos import GEOSGeometry

from apps.core.models import Spatial

import pytest

from apps.core.models.concepts import GeoLocation


@pytest.mark.django_db
def test_process_spatials():
    s1 = Spatial.objects.create(custom_wkt=["POINT (1 2 3)", "POINT (4 5)"])
    s2 = Spatial.objects.create(custom_wkt=["POLYGON ((0 0, 180 0, 180 90, 0 90, 0 0))"])
    s3 = Spatial.objects.create()
    s3.geolocations.add(
        GeoLocation.objects.create(
            geometry=GEOSGeometry(json.dumps({"type": "Point", "coordinates": [61, 35, 1000]}))
        )
    )
    s4 = Spatial.objects.create(custom_wkt=["POÄNG )1337(", "POINT (0      0)"])

    call_command("process_spatial_geometries")
    for spatial in [s1, s2, s3, s4]:
        spatial.refresh_from_db()

    assert s1.geolocations.all()[0].geometry_2d.wkt == "POINT (1 2)"
    assert s1.geolocations.all()[0].geometry_3d.wkt == "POINT Z (1 2 3)"
    assert s1.geolocations.all()[1].geometry_2d.wkt == "POINT (4 5)"
    assert s1.geolocations.all()[1].geometry_3d is None

    assert s2.geolocations.all()[0].geometry_2d.geom_type == "Polygon"
    s2.geolocations.all()[0].geometry_3d is None

    assert s3.geolocations.all()[0].geometry_2d.wkt == "POINT (61 35)"
    assert s3.geolocations.all()[0].geometry_3d.wkt == "POINT Z (61 35 1000)"

    # Invalid WKT -> can't create geolocations
    assert s4.custom_wkt == ["POÄNG )1337(", "POINT (0      0)"]
    assert s4.geolocations.count() == 0
