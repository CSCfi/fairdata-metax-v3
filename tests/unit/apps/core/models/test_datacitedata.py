import pytest

from apps.common.datacitedata import Datacitedata


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
def test_get_wkt_data_point(wkt, is_ok):
    dd = Datacitedata()
    data = dd.get_wkt_data([wkt])
    if is_ok:
        assert data.get("geoLocationPoint") is not None
    else:
        assert data.get("geoLocationPoint") is None


@pytest.mark.parametrize(
    "wkt, is_ok",
    [
        ["POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))", True],
        ["POLYGON ((30 10, 40 40, 20 40, 1234 20, 30 10))", False], # Invalid longitude
        ["POLYGON ((30 10, 40 40, 20 40, 10 20))", False], # Loop not closed
    ],
)
def test_get_wkt_data_polygon(wkt, is_ok):
    dd = Datacitedata()
    data = dd.get_wkt_data([wkt])
    if is_ok:
        assert data.get("geoLocationPolygons") is not None
    else:
        assert data.get("geoLocationPolygons") is None
