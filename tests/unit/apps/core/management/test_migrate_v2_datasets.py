from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = [pytest.mark.django_db, pytest.mark.management]


def test_migrate_command(mock_response, reference_data):
    out = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=StringIO(), all=True, allow_fail=True)
    assert "successfully migrated" in out.getvalue().strip()


def test_migrate_command_error(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, all=True, identifiers="123 5423")
    assert err.getvalue().strip() == "--identifiers and --all are mutually exclusive"


def test_migrate_command_identifier(mock_response_single, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        identifiers="c955e904-e3dd-4d7e-99f1-3fed446f96d1",
    )
    assert "successfully migrated" in out.getvalue().strip()
