import pytest
from rest_framework import serializers

from apps.common.serializers.fields import MultiLanguageField


def test_multi_language_field():
    field = MultiLanguageField()
    assert field.to_internal_value({"fi": "Käännös", "en": "", "sv": None}) == {"fi": "Käännös"}


def test_multi_language_field_null():
    field = MultiLanguageField(allow_null=True)
    assert field.to_internal_value({"nothing": ""}) == None


def test_multi_language_field_null_not_allowed():
    with pytest.raises(serializers.ValidationError):
        field = MultiLanguageField(allow_null=False)
        field.to_internal_value({})
