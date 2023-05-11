import pytest
import logging
from rest_framework import serializers

from apps.core.serializers import SpatialModelSerializer

logger = logging.getLogger(__name__)


def test_create_spatial_without_url():
    """Should return Validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer()
        ser.create({})
        assert "Spatial needs url, got None" in str(error.value)


@pytest.mark.django_db
def test_create__with_non_existing_url(location_reference_data):
    """Should throw an validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer()
        ser.create({"url": "https://test.com"})
        assert "Location not found https://test.com" in str(error.value)


@pytest.mark.django_db
def test_create_dataset_license_with_exsiting_url(location_reference_data):
    """Should create a Spatial."""
    ser = SpatialModelSerializer()
    spatial = ser.create({"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"})
    assert spatial is not None


@pytest.mark.django_db
def test_udpate_spatial_with_invalid_url(location_reference_data):
    """Should throw a validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer()
        spatial = ser.create({"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"})
        ser.update(spatial, {"url": "https://diipadaapa.com"})
        assert "Location not found https://diipadaapa.com" in str(error.value)


@pytest.mark.django_db
def test_udpate_spatial(location_reference_data):
    """Should update spatial."""
    ser = SpatialModelSerializer()
    spatial = ser.create({"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"})
    updated = ser.update(spatial, {"url": "http://www.yso.fi/onto/yso/p105080"})
    assert updated.reference.url == "http://www.yso.fi/onto/yso/p105080"
