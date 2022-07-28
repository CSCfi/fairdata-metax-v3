import pytest
from unittest.mock import call

from django.test import override_settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.refdata.models import FieldOfScience, Keyword, Location

TEST_DATA_SOURCES = {
    "field_of_science": {
        "model": "refdata.FieldOfScience",
        "importer": "Finto",
        "source": "https://testdata/field_of_science",
    },
    "keyword": {
        "model": "refdata.Keyword",
        "importer": "Finto",
        "source": "https://testdata/keyword",
    },
    "location": {
        "model": "refdata.Location",
        "importer": "FintoLocation",
        "source": "https://testdata/location",
    },
}


@pytest.fixture
def mock_importers(mocker):
    finto = mocker.patch("apps.refdata.services.indexer.FintoImporter")
    return {
        "Finto": finto,
        "FintoLocation": mocker.patch(
            "apps.refdata.services.indexer.FintoLocationImporter"
        ),
    }


@override_settings(REFERENCE_DATA_SOURCES=TEST_DATA_SOURCES)
def test_import_all(mock_importers):
    call_command("index_reference_data")
    mock_importers["Finto"].assert_has_calls(
        [
            call(
                model=FieldOfScience,
                source=TEST_DATA_SOURCES["field_of_science"]["source"],
            ),
            call(model=Keyword, source=TEST_DATA_SOURCES["keyword"]["source"]),
        ]
    )
    mock_importers["FintoLocation"].assert_called_once_with(
        model=Location,
        source=TEST_DATA_SOURCES["location"]["source"],
    )
    mock_importers["Finto"].return_value.load.assert_called()
    mock_importers["FintoLocation"].return_value.load.assert_called()


@override_settings(REFERENCE_DATA_SOURCES=TEST_DATA_SOURCES)
def test_import_specific(mock_importers):
    call_command("index_reference_data", "field_of_science", "location")
    mock_importers["Finto"].assert_called_once_with(
        model=FieldOfScience,
        source=TEST_DATA_SOURCES["field_of_science"]["source"],
    )
    mock_importers["FintoLocation"].assert_called_once_with(
        model=Location,
        source=TEST_DATA_SOURCES["location"]["source"],
    )
    mock_importers["Finto"].return_value.load.assert_called()
    mock_importers["FintoLocation"].return_value.load.assert_called()


@override_settings(REFERENCE_DATA_SOURCES=TEST_DATA_SOURCES)
def test_import_unknown_type():
    with pytest.raises(CommandError):
        call_command("index_reference_data", "field_of_science", "something")


@override_settings(REFERENCE_DATA_SOURCES=TEST_DATA_SOURCES)
def test_import_duplicate_type():
    with pytest.raises(CommandError):
        call_command("index_reference_data", "field_of_science", "field_of_science")
