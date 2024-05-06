import os
from base64 import b64decode
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.core.models import LegacyDataset

pytestmark = [pytest.mark.django_db, pytest.mark.management, pytest.mark.adapter]


@pytest.fixture(autouse=True)
def integration_settings(settings):
    settings.METAX_V2_HOST = "https://metax-v2-test"
    settings.METAX_V2_USER = "metax-v3-user"
    settings.METAX_V2_PASSWORD = "metax-v3-password"
    return settings


def test_migrate_command(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_datasets", stdout=out, stderr=err, use_env=True, allow_fail=True)
    assert "10 datasets updated succesfully" in out.getvalue().strip()
    assert "Invalid identifier 'invalid', ignoring" in err.getvalue()


def test_migrate_command_error(mock_response, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        use_env=True,
        catalogs=["123"],
        identifiers="123 5423",
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
    call_command("migrate_v2_datasets", stdout=out, stderr=err, use_env=True, file=filepath)
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
        use_env=True,
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
            use_env=True,
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
        use_env=True,
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
        use_env=True,
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
        use_env=True,
        stop_after=1,
        catalogs=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert "1 datasets updated" in out.getvalue()


def test_migrate_command_update(mock_response_single, reference_data):
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
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
    assert err.getvalue() == ""
    output = out.getvalue()
    assert "Processed 1 datasets" in output
    assert "0 datasets updated succesfully" in output


def test_migrate_command_update_wrong_api_version(mock_response_single, reference_data):
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    out = StringIO()
    err = StringIO()
    LegacyDataset.objects.filter(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1").update(api_version=3)
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        update=True,
        force=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert err.getvalue() == ""
    output = out.getvalue()
    assert (
        "Dataset 'c955e904-e3dd-4d7e-99f1-3fed446f96d1' has been modified in V3, not updating"
        in output
    )
    assert "Processed 1 datasets" in output
    assert "0 datasets updated succesfully" in output


def test_migrate_command_update_wrong_api_version_in_v2(
    mock_response_api_version_3, reference_data
):
    out = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    assert "from a later Metax version, ignoring" in out.getvalue()


def test_migrate_command_update_draft(mock_response_draft, reference_data):
    out = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    assert "is not published, ignoring" in out.getvalue()


def test_migrate_command_update_file(mock_response_single, reference_data):
    err = StringIO()
    call_command("migrate_v2_datasets", stderr=err, update=True, file="somefile")
    assert "The --file and --update options are mutually exclusive." in err.getvalue().strip()


def test_migrate_missing_args():
    err = StringIO()
    call_command("migrate_v2_datasets", stderr=err)
    assert "Metax instance not specified and not using --file or --update." in err.getvalue()


def test_migrate_prompt_credentials(requests_mock):
    mock = requests_mock.get(url="https://metax-v2-test/rest/v2/datasets", json={"results": []})
    err = StringIO()
    with patch("builtins.input", lambda x: "username"), patch(
        "getpass.getpass", lambda x: "password"
    ):
        call_command("migrate_v2_datasets", stderr=err, use_env=True, prompt_credentials=True)
    assert err.getvalue() == ""
    assert mock.call_count == 2
    auth = mock.last_request.headers["authorization"]
    assert b64decode(auth.replace("Basic ", "")) == b"username:password"
