import pytest

from apps.core.models.legacy_converter import LegacyDatasetConverter


@pytest.fixture
def converter():
    return LegacyDatasetConverter(dataset_json={}, convert_only=True)


def test_is_valid_wkt(converter):
    assert converter.is_valid_wkt("POINT (1.2 3.4)") is True
    assert converter.is_valid_wkt("point(1.2 3.4)") is True
    assert converter.is_valid_wkt("60° 15′ 11″ N, 24° 4′ 4″ E") is False
