import os
from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = [pytest.mark.django_db, pytest.mark.management]


def test_migrate_command(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, all=True, allow_fail=True)
    assert "10 datasets updated succesfully" in out.getvalue().strip()
    assert "Invalid identifier 'invalid', ignoring" in err.getvalue()


def test_migrate_command_error(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, all=True, identifiers="123 5423")
    assert (
        err.getvalue().strip() == "Exactly one of --identifiers, --catalogs and --all is required."
    )


def test_migrate_command_missing_arg(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err)
    assert (
        err.getvalue().strip() == "Exactly one of --identifiers, --catalogs and --all is required."
    )


def test_migrate_command_identifier(mock_response_single, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert "1 datasets updated succesfully" in out.getvalue().strip()


def test_migrate_command_identifier_error_in_data(mock_response_single_invalid, reference_data):
    out = StringIO()
    err = StringIO()
    with pytest.raises(ValueError):
        call_command(
            "migrate_v2_datasets",
            stdout=out,
            stderr=err,
            identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        )


def test_migrate_command_allow_fail(mock_response_single_invalid, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        allow_fail=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )

    assert "Value is not a list: porkkana" in err.getvalue()
    assert "1 datasets failed" in out.getvalue().strip()


def test_migrate_command_catalog(mock_response_single_catalog, mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        catalogs=["c955e904-e3dd-4d7e-99f1-3fed446f96d1", "unknown_catalog"],
    )
    assert "Migrating catalog: c955e904-e3dd-4d7e-99f1-3fed446f96d1" in out.getvalue()
    assert "Invalid catalog identifier: unknown_catalog" in err.getvalue()
    assert "10 datasets updated" in out.getvalue()


def test_migrate_command_catalog_stop_after(
    mock_response_single_catalog, mock_response, reference_data
):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        stop_after=1,
        catalogs=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert "1 datasets updated" in out.getvalue()


def test_migrate_command_file(mock_response_single_catalog, mock_response, reference_data):
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "legacy_metax_datasets.json"
    )
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, file=filepath, all=True)
    assert "Invalid identifier 'invalid', ignoring" in err.getvalue()
    assert "5 datasets updated" in out.getvalue()
