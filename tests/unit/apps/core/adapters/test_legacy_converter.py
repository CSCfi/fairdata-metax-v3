import pytest

from apps.core.factories import LocationFactory
from apps.core.models.legacy_converter import LegacyDatasetConverter

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


def test_invalid_spatial_as_wkt(converter):
    spatial = {
        "geographic_name": "Alt is a number",
        "alt": "100.123",
        "as_wkt": ["ei tää oo wkt"],
    }
    converter.convert_spatial(spatial)
    assert spatial["_invalid"]["fields"] == ["as_wkt"]


def test_invalid_spatial_multiple_errors(converter):
    spatial = {
        "geographic_name": "Alt is not a number",
        "alt": "100 metriä",
        "as_wkt": ["ei tää oo wkt"],
    }
    converter.convert_spatial(spatial)
    assert set(spatial["_invalid"]["fields"]) == {"alt", "as_wkt"}
