import uuid

import fastuuid
import pytest
import shapely
from django.contrib.gis.geos import GEOSGeometry

from apps.common.helpers import (
    get_sql,
    merge_sets,
    normalize_doi,
    uuid7,
    get_geometry_bounds,
    split_geometry_long_edges,
)
from apps.core.models.catalog_record.dataset import Dataset


def test_merge_sets():
    joined = merge_sets(
        [
            [1, 2, 3],
            [3, 4],
            [5, 3],
            [6],
            [7, 8],
            [7, 9],
            [10, 6],
            [11],
            [2, 12],
        ]
    )
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[1, 2, 3, 4, 5, 12], [6, 10], [7, 8, 9], [11]]


def test_merge_sets_2():
    joined = merge_sets([[1, 2], [3, 4], [2, 3]])
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[1, 2, 3, 4]]


def test_merge_sets_3():
    joined = merge_sets(
        [
            [8, 100],
            [120, 8],
            [0],
            [1, 2],
            [9, 8],
            [2, 3],
            [8, 7],
            [3, 4],
            [7, 6],
            [4, 5],
            [6, 5],
            [10, 1],
            [2, 7],
            [15, 14, 8, 12],
        ]
    )
    joined = sorted(sorted(v) for v in joined)
    assert joined == [[0], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 100, 120]]


def test_normalize_doi():
    assert normalize_doi("10.1000/123") == "doi:10.1000/123"
    assert normalize_doi("doi:10.1000/123") == "doi:10.1000/123"
    assert normalize_doi("http://doi.org/10.1000/123") == "doi:10.1000/123"
    assert normalize_doi("https://doi.org/10.1000/123") == "doi:10.1000/123"
    assert normalize_doi("https://notadoi.org/10.1000/123") is None
    assert normalize_doi("12.345/67") is None


def test_uuid7():
    """Test UUIDv7 value remains unchanged between `uuid` and `fastuuid` libraries."""
    std_id: uuid.UUID = uuid7()
    fast_id = fastuuid.UUID(bytes=std_id.bytes)
    std_id_2 = uuid.UUID(bytes=fast_id.bytes)
    assert str(std_id) == str(fast_id) == str(std_id_2)


@pytest.mark.django_db
def test_get_sql():
    """Test that get_sql returns a SQL string where parameters are in quotes."""
    sql = get_sql(
        Dataset.objects.order_by().values("id").filter(id="00000000-0000-0000-0000-000000001234")
    )
    assert "'00000000000000000000000000001234'" in sql


def test_get_geometry_bounds():
    wkt = "POLYGON ((-50 -50, 30 -70, 40 50, -50 -50))"

    assert get_geometry_bounds(GEOSGeometry(wkt)) == [[-50, -70], [40, 50]]
    assert get_geometry_bounds(shapely.from_wkt(wkt)) == [[-50, -70], [40, 50]]


def test_split_geometry_long_edges():
    wkt = "LINESTRING (-90 0, 90 0)" # len >= 180, should split
    assert split_geometry_long_edges(GEOSGeometry(wkt)).wkt == "LINESTRING (-90 0, 0 0, 90 0)"
    assert split_geometry_long_edges(shapely.from_wkt(wkt)).wkt == "LINESTRING (-90 0, 0 0, 90 0)"

def test_split_geometry_long_edges_no_split():
    wkt = "LINESTRING (-80 0, 80 0)" # len < 180, no need to split
    assert split_geometry_long_edges(GEOSGeometry(wkt)).wkt == "LINESTRING (-80 0, 80 0)"
    assert split_geometry_long_edges(shapely.from_wkt(wkt)).wkt == "LINESTRING (-80 0, 80 0)"




