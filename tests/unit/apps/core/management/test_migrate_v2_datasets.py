import os
from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = [pytest.mark.django_db, pytest.mark.management]


def test_migrate_command(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, allow_fail=True)
    assert "10 datasets updated succesfully" in out.getvalue().strip()
    assert "Invalid identifier 'invalid', ignoring" in err.getvalue()


def test_migrate_command_error(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets", stdout=out, stderr=err, catalogs=["123"], identifiers="123 5423"
    )
    assert (
        err.getvalue().strip()
        == "The --identifiers and --catalogs options are mutually exclusive."
    )


def test_migrate_command_file(mock_response_single_catalog, mock_response, reference_data):
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "legacy_metax_datasets.json"
    )
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, file=filepath)
    assert "Invalid identifier 'invalid', ignoring" in err.getvalue()
    output = out.getvalue()
    assert "5 datasets updated" in output
    assert "Ignored invalid legacy data:\n- research_dataset.rights_holder[0]" in output


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


def test_migrate_command_update(mock_response_single, reference_data):
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        update=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    output = out.getvalue()
    assert "Processed 1 datasets" in output
    assert "0 datasets updated succesfully" in output


def test_migrate_command_update_file(mock_response_single, reference_data):
    err = StringIO()
    call_command("migrate_v2_datasets", stderr=err, update=True, file="somefile")
    assert "The --file and --update options are mutually exclusive." in err.getvalue().strip()
