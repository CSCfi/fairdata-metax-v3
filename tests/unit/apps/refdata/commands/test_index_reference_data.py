from unittest.mock import call

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.refdata.models import (
    AccessType,
    FieldOfScience,
    FileFormatVersion,
    License,
    Location,
    Theme,
)

TEST_DATA_SOURCES = {
    "field_of_science": {
        "model": "refdata.FieldOfScience",
        "importer": "Finto",
        "source": "https://testdata/field_of_science",
    },
    "theme": {
        "model": "refdata.Theme",
        "importer": "Finto",
        "source": "https://testdata/theme",
    },
    "location": {
        "model": "refdata.Location",
        "importer": "FintoLocation",
        "source": "https://testdata/location",
    },
    "access_type": {
        "model": "refdata.AccessType",
        "importer": "LocalJSON",
        "source": "access_type.json",
        "scheme": "https://schemes/access_type",
    },
    "license": {
        "model": "refdata.License",
        "importer": "LocalJSONLicense",
        "source": "license.json",
        "scheme": "https://schemes/license",
    },
    "file_format_version": {
        "model": "refdata.FileFormatVersion",
        "importer": "LocalJSONFileFormatVersion",
        "source": "file_format_version.json",
        "scheme": "https://schemes/file_format_version",
    },
}


@pytest.fixture
def mock_importers(mocker):
    return {
        "Finto": mocker.patch("apps.refdata.services.indexer.FintoImporter"),
        "FintoLocation": mocker.patch(
            "apps.refdata.services.indexer.FintoLocationImporter"
        ),
        "LocalJSON": mocker.patch("apps.refdata.services.indexer.LocalJSONImporter"),
        "LocalJSONFileFormatVersion": mocker.patch(
            "apps.refdata.services.indexer.LocalJSONFileFormatVersionImporter"
        ),
        "LocalJSONLicense": mocker.patch(
            "apps.refdata.services.indexer.LocalJSONLicenseImporter"
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
                scheme=None,
            ),
            call(
                model=Theme,
                source=TEST_DATA_SOURCES["theme"]["source"],
                scheme=None,
            ),
        ]
    )
    mock_importers["FintoLocation"].assert_called_once_with(
        model=Location,
        source=TEST_DATA_SOURCES["location"]["source"],
        scheme=None,
    )
    mock_importers["LocalJSON"].assert_called_once_with(
        model=AccessType,
        source=TEST_DATA_SOURCES["access_type"]["source"],
        scheme=TEST_DATA_SOURCES["access_type"]["scheme"],
    )
    mock_importers["LocalJSONLicense"].assert_called_once_with(
        model=License,
        source=TEST_DATA_SOURCES["license"]["source"],
        scheme=TEST_DATA_SOURCES["license"]["scheme"],
    )
    mock_importers["LocalJSONFileFormatVersion"].assert_called_once_with(
        model=FileFormatVersion,
        source=TEST_DATA_SOURCES["file_format_version"]["source"],
        scheme=TEST_DATA_SOURCES["file_format_version"]["scheme"],
    )
    for importer in mock_importers.values():
        # Check .load() is called for an instance of each importer type
        importer.return_value.load.assert_called()


@override_settings(REFERENCE_DATA_SOURCES=TEST_DATA_SOURCES)
def test_import_specific(mock_importers):
    call_command("index_reference_data", "field_of_science", "location")
    mock_importers["Finto"].assert_called_once_with(
        model=FieldOfScience,
        source=TEST_DATA_SOURCES["field_of_science"]["source"],
        scheme=None,
    )
    mock_importers["FintoLocation"].assert_called_once_with(
        model=Location, source=TEST_DATA_SOURCES["location"]["source"], scheme=None
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
