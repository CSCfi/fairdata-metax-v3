from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework import serializers

pytestmark = [pytest.mark.django_db, pytest.mark.management]


def test_migrate_command(mock_response, reference_data):
    out = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=StringIO(), all=True, allow_fail=True)
    assert "successfully migrated" in out.getvalue().strip()


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
    assert "successfully migrated" in out.getvalue().strip()


def test_migrate_command_identifier_error_in_data(mock_response_single_invalid, reference_data):
    out = StringIO()
    err = StringIO()
    with pytest.raises(serializers.ValidationError):
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
    assert "failed to migrate" in out.getvalue().strip()


def test_migrate_command_catalog(mock_response_single_catalog, mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        catalogs=["c955e904-e3dd-4d7e-99f1-3fed446f96d1", "unknown_catalog"],
    )
    assert "successfully migrated" in out.getvalue().strip()


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
    assert "successfully migrated 1" in out.getvalue().strip()
