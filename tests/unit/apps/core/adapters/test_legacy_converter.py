import pytest

from apps.core.models.legacy_converter import LegacyDatasetConverter
from apps.core.factories import LocationFactory

pytestmark = [pytest.mark.adapter]


@pytest.fixture
def converter():
    return LegacyDatasetConverter(dataset_json={}, convert_only=True)


def test_convert_spatial(converter):
    LocationFactory(
        url="http://www.yso.fi/onto/yso/p508763",
        pref_label={"fi": "Alppikylä (Helsinki)", "sv": "Alpbyn (Helsingfors)"},
        in_scheme="http://www.yso.fi/onto/yso/places",
        as_wkt="POINT (25.06677 60.25873)",
    )

    # as_wkt matches place_uri location, omit from custom_wkt
    spatial = converter.convert_spatial(
        {
            "place_uri": {
                "identifier": "http://www.yso.fi/onto/yso/p508763",
            },
            "as_wkt": ["POINT (25.06677 60.25873)"],
        }
    )
    assert spatial["reference"]["pref_label"]["fi"] == "Alppikylä (Helsinki)"
    assert spatial["custom_wkt"] == None

    # as_wkt does not match place_uri location, keep in custom_wkt
    spatial = converter.convert_spatial(
        {
            "place_uri": {
                "identifier": "http://www.yso.fi/onto/yso/p508763",
            },
            "as_wkt": ["POINT (27.06677 -30.25873)"],
        }
    )
    assert spatial["reference"]["pref_label"]["fi"] == "Alppikylä (Helsinki)"
    assert spatial["custom_wkt"] == ["POINT (27.06677 -30.25873)"]


def test_is_valid_wkt(converter):
    assert converter.is_valid_wkt("POINT (1.2 3.4)") is True
    assert converter.is_valid_wkt("point(1.2 3.4)") is True
    assert converter.is_valid_wkt("60° 15′ 11″ N, 24° 4′ 4″ E") is False
