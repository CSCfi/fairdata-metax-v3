import pytest
from rest_framework import serializers

from apps.common.serializers.fields import (
    MultiLanguageField,
    NullableCharField,
    CommaSeparatedListField,
)


def validate_input(field, input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            field.run_validation(input)
    else:
        assert field.run_validation(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("first,second,third", ["first", "second", "third"]),
        ("a,,b", serializers.ValidationError),
        ("1,2", ["1", "2"]),
    ],
)
def test_comma_separated_field(input, expected):
    field = CommaSeparatedListField(child=serializers.CharField())
    validate_input(field, input, expected)


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


def test_nullable_char_field():
    field = NullableCharField(allow_null=True)
    assert field.run_validation("     ") == None
    field = NullableCharField(allow_null=True, trim_whitespace=False)
    assert field.run_validation("     ") == "     "
