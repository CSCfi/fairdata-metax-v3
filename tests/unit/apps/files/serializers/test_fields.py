import pytest
from rest_framework import serializers

from apps.common.serializers.fields import WKTField
from apps.files.serializers import fields


def validate_input(field, input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            field.run_validation(input)
    else:
        assert field.run_validation(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("tiedosto.txt", "tiedosto.txt"),
        (" tiedosto.txt ", " tiedosto.txt "),
        ("/data/tiedosto.txt", serializers.ValidationError),
        ("tiedosto.txt/", serializers.ValidationError),
        ("ti/edo/sto.txt", serializers.ValidationError),
    ],
)
def test_filename_field(input, expected):
    field = fields.FileNameField()
    validate_input(field, input, expected)


@pytest.mark.parametrize(
    "input,expected",
    [
        ("/data/tiedosto.txt", "/data/tiedosto.txt"),
        ("/data/tiedosto.txt  ", "/data/tiedosto.txt  "),
        ("/ti/edo/sto.txt", "/ti/edo/sto.txt"),
        ("/data/polku/", serializers.ValidationError),
        ("/data//tiedosto.txt", serializers.ValidationError),
        ("tiedosto.txt", serializers.ValidationError),
        (" /tiedosto.txt", serializers.ValidationError),
    ],
)
def test_file_path_field(input, expected):
    field = fields.FilePathField()
    validate_input(field, input, expected)


@pytest.mark.parametrize(
    "input,expected",
    [
        ("/", "/"),
        ("/data/polku/", "/data/polku/"),
        ("/data/polku", serializers.ValidationError),
        (" /data/polku", serializers.ValidationError),
        ("/data//polku", serializers.ValidationError),
        ("tiedosto.txt", serializers.ValidationError),
        (" /tiedosto.txt", serializers.ValidationError),
    ],
)
def test_directory_path_field(input, expected):
    field = fields.DirectoryPathField()
    validate_input(field, input, expected)


@pytest.mark.parametrize(
    "input,expected",
    [
        ("/", "/"),
        ("/data/polku/", "/data/polku/"),
        ("/data/polku", "/data/polku/"),
        (" /data/polku", serializers.ValidationError),
    ],
)
def test_optional_slash_directory_path_field(input, expected):
    field = fields.OptionalSlashDirectoryPathField()
    validate_input(field, input, expected)


def test_list_valid_choices_field_error_text():
    field = fields.ListValidChoicesField(
        choices=(("first", "first choice"), ("second", "second choice"))
    )
    with pytest.raises(serializers.ValidationError) as excinfo:
        field.to_internal_value("moro")
    assert "Valid choices are: ['first', 'second']" in excinfo.value.detail[0]


def test_wktfield_ok():
    field = WKTField()
    field.to_internal_value("POINT(1.0 2.0)")


def test_wktfield_invalid_wkt():
    field = WKTField()
    with pytest.raises(serializers.ValidationError) as excinfo:
        field.to_internal_value("POINT(1")
    assert "Invalid WKT:" in excinfo.value.detail[0]


def test_wktfield_invalid_wkt_migrating():
    class WKTSerializer(serializers.Serializer):
        value = WKTField()

    serializer = WKTSerializer(data={"value": "POINT(1"})
    assert not serializer.is_valid()

    serializer = WKTSerializer(data={"value": "POINT(1"}, context={"migrating": True})
    assert serializer.is_valid()
