import pytest

from apps.core import factories
from apps.core.helpers import normalize_spatial_wkts
from apps.core.models import Spatial


@pytest.mark.django_db
def test_normalize_spatial_wkts():
    spatial1 = factories.SpatialFactory(custom_wkt=[" POINT   (50.0  50   ) "])
    spatial2 = factories.SpatialFactory(custom_wkt=["POINT (25 30)"])
    assert normalize_spatial_wkts(Spatial.objects.all()) == 1  # one update
    spatial1.refresh_from_db()
    assert spatial1.custom_wkt == ["POINT (50 50)"]

    spatial2.refresh_from_db()
    assert spatial2.custom_wkt == ["POINT (25 30)"]
