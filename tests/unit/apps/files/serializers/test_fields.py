import pytest
from rest_framework import serializers

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
        ("first,second,third", ["first", "second", "third"]),
        ("a,,b", serializers.ValidationError),
        ("1,2", ["1", "2"]),
    ],
)
def test_comma_separated_field(input, expected):
    field = fields.CommaSeparatedListField(child=serializers.CharField())
    validate_input(field, input, expected)


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
def test_file_name_field(input, expected):
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
    try:
        field.to_internal_value("moro")
        assert False
    except serializers.ValidationError as error:
        assert "Valid choices are: ['first', 'second']" in error.detail[0]
