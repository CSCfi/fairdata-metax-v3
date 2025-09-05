import logging

import pytest
from rest_framework import serializers

from apps.core.serializers import LicenseModelSerializer
from apps.refdata.models import License

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db]


def test_create_dataset_license_without_url_and_custom_url():
    """Should return Validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = LicenseModelSerializer()
        ser.create({})
        assert "License needs url or custom_url, got None" in str(error.value)


def test_create_dataset_license_with_custom_url(license_reference_data):
    """Should automatically fill reference to use other license."""
    ser = LicenseModelSerializer()
    license = ser.create({"custom_url": "https://test.com"})
    assert license.reference.url == "http://uri.suomi.fi/codelist/fairdata/license/code/other"
    assert license.custom_url == "https://test.com"


def test_create_dataset_license_with_non_existing_url(license_reference_data):
    """Should return Validation error."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = LicenseModelSerializer()
        ser.create({"url": "http://diipadaapa.co.uk"})
        assert "License not found http://diipadaapa.co.uk" in str(error.value)


def test_update_dataset_license_with_invalid_url(license_reference_data):
    """Should automatically fill reference to use other license."""
    with pytest.raises(serializers.ValidationError) as error:
        ser = LicenseModelSerializer()
        license = ser.create({"custom_url": "https://test.com"})
        ser.update(license, {"url": "https://diipadaapa.com"})
        assert "License not found https://diipadaapa.com" in str(error.value)


def test_update_dataset_license(license_reference_data):
    """Should automatically fill reference to use other license."""
    ser = LicenseModelSerializer()
    license = ser.create({"custom_url": "https://test.com"})
    updated = ser.update(license, {"custom_url": "https://diipadaapa.com"})
    assert updated.custom_url == "https://diipadaapa.com"


def test_invalid_license_title(license_reference_data):
    """Should require license title to be a dict."""
    ser = LicenseModelSerializer(data={"custom_url": "https://a.com", "title": "jeejee"})
    assert not ser.is_valid()

    ser = LicenseModelSerializer(data={"custom_url": "https://a.com", "title": {"en": "jeejee"}})
    assert ser.is_valid()
