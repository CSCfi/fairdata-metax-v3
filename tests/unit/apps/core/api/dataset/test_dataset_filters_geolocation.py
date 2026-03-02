import pytest
from django.contrib.gis.geos import Point, Polygon
from apps.core import factories

@pytest.mark.parametrize(
    "distance,geometry,count",
    [
        (2000, Point(25.349000,60.554000), 2),  # Point and polygon found
        (200, Point(25.346204,60.563359), 1),  # Only polygon found
        (2000, Point(25.281321, 60.559791), 0),  # No matches
    ],
)
def test_geolocation_filter_geometries_using_distance(admin_client, distance, geometry, count):
    dataset_a = factories.DatasetFactory(title={"en": "Test point"})
    dataset_a.spatial.set([factories.SpatialFactory(geographic_name="Isojärvi keskusta", geolocations__geometry=Point(25.349782,60.554031))])

    dataset_b = factories.DatasetFactory(title={"en": "Test polygon"})
    dataset_b.spatial.set([factories.SpatialFactory(geographic_name="Isojärvi alue",
                                                  geolocations__geometry=Polygon((
                                                            (25.342926, 60.564129),
                                                            (25.331223, 60.555535),
                                                            (25.347451, 60.542663),
                                                            (25.355349, 60.543422),
                                                            (25.372005, 60.553086),
                                                            (25.365911, 60.554944),
                                                            (25.369176, 60.559460),
                                                            (25.359904, 60.563808),
                                                            (25.342926, 60.564129))))])

    res = admin_client.get(f"/v3/datasets?distance={distance}&geolocation={geometry}")
    assert res.status_code == 200, res.data
    assert res.data["count"] == count


@pytest.mark.parametrize(
    "geometry,count",
    [
        (Point(25.36546,60.55563), 2),  # Both polygons found
        (Point(25.346204,60.563359), 1),  # One polygon found
        (Point(25.281321, 60.559791), 0),  # No matches
        (Polygon(((25.34572, 60.55600), (25.34572, 60.54600), (25.37765, 60.54600),
                 (25.37765, 60.55600), (25.34572, 60.55600))),3), # Match all
        (Polygon(((25.31610, 60.56534), (25.32194, 60.53689), (25.40279, 60.53884),
                  (25.39258, 60.57014), (25.31610, 60.56534))), 3)  # All matches inside polygon
    ],
)
def test_geolocation_filter_polygon_overlapping(admin_client, geometry, count):
    dataset_a = factories.DatasetFactory(title={"en": "Test point"})
    dataset_a.spatial.set([factories.SpatialFactory(geographic_name="Isojärvi keskusta", geolocations__geometry=Point(25.349782,60.554031))])

    dataset_b = factories.DatasetFactory(title={"en": "Test polygon"})
    dataset_b.spatial.set([factories.SpatialFactory(geographic_name="Isojärvi alue",
                                                  geolocations__geometry=Polygon((
                                                            (25.342926, 60.564129),
                                                            (25.331223, 60.555535),
                                                            (25.347451, 60.542663),
                                                            (25.355349, 60.543422),
                                                            (25.372005, 60.553086),
                                                            (25.365911, 60.554944),
                                                            (25.369176, 60.559460),
                                                            (25.359904, 60.563808),
                                                            (25.342926, 60.564129))))])

    dataset_c = factories.DatasetFactory(title={"en": "Overlapping polygon"})
    dataset_c.spatial.set([factories.SpatialFactory(geolocations__geometry=Polygon(((25.36400, 60.55694),
                                                                (25.36400, 60.55300),
                                                                (25.37350, 60.55300),
                                                                (25.37350, 60.55694),
                                                                (25.36400, 60.55694))))])

    res = admin_client.get(f"/v3/datasets?geolocation={geometry}")
    assert res.status_code == 200, res.data
    assert res.data["count"] == count
