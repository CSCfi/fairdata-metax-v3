import copy
import json

import pytest
from rest_framework import serializers

from apps.common.serializers.fields import (
    CommaSeparatedListField,
    MultiLanguageField,
    NullableCharField,
    PrivateEmailField,
    PrivateEmailValue,
    handle_private_emails,
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


def test_email_field():
    email1 = "teppo@example.com"
    email2 = "matti@example.com"
    field = PrivateEmailField()

    assert field.to_representation(email1) == field.to_representation(email1)
    assert field.to_representation(email1) != field.to_representation(email2)
    assert isinstance(field.to_representation(email1), PrivateEmailValue)
    assert str(field.to_representation(email1)) == "<PrivateEmailValue>"

    assert field.to_representation(email1).value == email1
    assert field.to_representation(email2).value == email2

    # PrivateEmailValues are not JSON serializable
    with pytest.raises(TypeError):
        json.dumps(field.to_representation(email1))


def test_handle_private_emails():
    value1 = PrivateEmailValue("teppo@example.com")
    value2 = PrivateEmailValue("matti@example.com")
    data = {"field": "value", "emal": value1, "more": [{"here": value2}]}

    # Convert values to strings
    data_show = copy.deepcopy(data)
    handle_private_emails(data_show, show_emails=True)
    assert data_show == {
        "field": "value",
        "emal": "teppo@example.com",
        "more": [{"here": "matti@example.com"}],
    }

    # Hide values
    data_hide = copy.deepcopy(data)
    handle_private_emails(data_hide, show_emails=False)
    assert data_hide == {
        "field": "value",
        "emal": "<hidden>",
        "more": [{"here": "<hidden>"}],
    }
