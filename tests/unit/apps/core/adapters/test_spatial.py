import logging

import pytest
from rest_framework import serializers

from apps.core.serializers import SpatialModelSerializer

logger = logging.getLogger(__name__)


def test_create_spatial_without_url():
    """Should return Validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer(data={})
        ser.is_valid(raise_exception=True)
        ser.save()
    assert "At least one of fields" in str(error.value) and "is required" in str(error.value)


@pytest.mark.django_db
def test_create__with_non_existing_url(location_reference_data):
    """Should throw an validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer(data={"reference": {"url": "https://test.com"}})
        ser.is_valid(raise_exception=True)
        ser.save()
    assert "Entry not found for url" in str(error.value)


@pytest.mark.django_db
def test_create_dataset_license_with_existing_url(location_reference_data):
    """Should create a Spatial."""
    ser = SpatialModelSerializer(
        data={"reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"}}
    )
    ser.is_valid(raise_exception=True)
    spatial = ser.save()
    assert spatial is not None


@pytest.mark.django_db
def test_update_spatial_with_invalid_url(location_reference_data):
    """Should throw a validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = SpatialModelSerializer(
            data={"reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"}}
        )
        ser.is_valid(raise_exception=True)
        spatial = ser.save()
        ser = SpatialModelSerializer(
            instance=spatial, data={"reference": {"url": "https://diipadaapa.com"}}
        )
        ser.is_valid(raise_exception=True)
        spatial = ser.save()
    assert "Entry not found for url " in str(error.value)


@pytest.mark.django_db
def test_update_spatial(location_reference_data):
    """Should update spatial."""
    ser = SpatialModelSerializer(
        data={"reference": {"url": "http://www.yso.fi/onto/onto/yso/c_9908ce39"}}
    )
    ser.is_valid(raise_exception=True)
    spatial = ser.save()
    ser = SpatialModelSerializer(
        instance=spatial, data={"reference": {"url": "http://www.yso.fi/onto/yso/p105080"}}
    )
    ser.is_valid(raise_exception=True)
    updated = ser.save()
    assert updated.reference.url == "http://www.yso.fi/onto/yso/p105080"
