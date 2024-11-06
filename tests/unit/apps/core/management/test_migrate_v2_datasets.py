import json
import os
import re
from base64 import b64decode
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils import timezone

from apps.core.models import Dataset, LegacyDataset
from apps.files.models import File, FileStorage

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.adapter,
    pytest.mark.usefixtures("data_catalog", "contract", "v2_integration_settings"),
]

match_start = r"^\d+ \(\d+ updated\):"
match_id = r".*identifier='(?P<identifier>[\w-]+?)'"
match_reason = r".*reason='(?P<reason>[\w-]+?)'"
match_created_objects = r".*created_objects=(?P<created_objects>\{.*?\})"
line_re = re.compile(match_start + match_id + match_reason + match_created_objects)


def parse_output_updates(output: str) -> list:
    """Parse updated dataset output lines of migrate_v2_datasets."""
    parsed = []
    lines = output.split("\n")
    for line in lines:
        match = line_re.match(line)
        if match:
            try:
                parsed.append(
                    dict(
                        identifier=match.group("identifier"),
                        reason=match.group("reason"),
                        created_objects=json.loads(
                            match.group("created_objects").replace("'", '"')
                        ),
                    )
                )
            except Exception:
                pass
    return parsed


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
    output = out.getvalue()
    errors = err.getvalue()
    assert "Errors for dataset" not in errors
    assert "Invalid identifier 'invalid', ignoring" in errors
    assert "10 datasets updated succesfully" in output


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


def test_migrate_command_identifier(mock_response_single, reference_data, legacy_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        use_env=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    output = out.getvalue()
    updates = parse_output_updates(output)
    assert updates == [
        {
            "identifier": "c955e904-e3dd-4d7e-99f1-3fed446f96d1",
            "reason": "created",
            "created_objects": {
                "Organization": 1,
                "FunderType": 1,
                "FileSet": 1,
                "FileSetFileMetadata": 1,
                "FileSetDirectoryMetadata": 1,
            },
        }
    ]
    assert "1 datasets updated succesfully" in output
    dataset = Dataset.objects.get(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1")
    assert str(dataset.permissions_id) == "4efd0669-33d4-4feb-93fb-5372d0f93a92"
    assert [user.username for user in dataset.permissions.editors.all()] == ["editor_user"]


def test_migrate_command_identifier_missing_files(mock_response_single, reference_data):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        use_env=True,
        allow_fail=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    errors = err.getvalue()

    assert "Missing files for dataset c955e904-e3dd-4d7e-99f1-3fed446f96d1" in errors


def test_migrate_command_file_offset(mock_response_single, reference_data, legacy_files):
    """Test migrating datasets with file offset and project prefix."""
    File.all_objects.update(
        legacy_id=F("legacy_id") + Value(100000000),
        storage_identifier=Concat(Value("100000000-"), F("storage_identifier")),
    )
    FileStorage.all_objects.update(csc_project=Concat(Value("100000000-"), F("csc_project")))

    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        use_env=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        file_offset=100000000,
    )
    output = out.getvalue()
    updates = parse_output_updates(output)
    assert updates == [
        {
            "identifier": "c955e904-e3dd-4d7e-99f1-3fed446f96d1",
            "reason": "created",
            "created_objects": {
                "Organization": 1,
                "FunderType": 1,
                "FileSet": 1,
                "FileSetFileMetadata": 1,
                "FileSetDirectoryMetadata": 1,
            },
        }
    ]
    assert "1 datasets updated succesfully" in output
    dataset = Dataset.objects.get(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1")
    assert str(dataset.permissions_id) == "4efd0669-33d4-4feb-93fb-5372d0f93a92"
    assert [user.username for user in dataset.permissions.editors.all()] == ["editor_user"]
    assert dataset.file_set.storage.csc_project == "100000000-2001479"
    assert dataset.file_set.files.count() == 3


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
        catalogs=["urn:nbn:fi:att:data-catalog-ida", "unknown_catalog"],
    )
    assert "Migrating catalog: urn:nbn:fi:att:data-catalog-ida" in out.getvalue()
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
        catalogs=["urn:nbn:fi:att:data-catalog-ida"],
    )
    assert "1 datasets updated" in out.getvalue()


def test_migrate_command_update(mock_response_single, reference_data, legacy_files):
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


def test_migrate_command_remigrate_modified(mock_response_single, reference_data, legacy_files):
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    out = StringIO()
    err = StringIO()

    # Update modification time, dataset should get updated
    dataset_json = mock_response_single["dataset"]._responses[0]._params["json"]
    dataset_json["date_modified"] = (timezone.now() + timedelta(weeks=2)).isoformat()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        stderr=err,
        use_env=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert err.getvalue() == ""
    output = out.getvalue()
    assert "Processed 1 datasets" in output
    assert "1 datasets updated succesfully" in output


def test_migrate_command_change_files(mock_response_single, reference_data, legacy_files):
    dataset_json = mock_response_single["dataset"]._responses[0]._params["json"]
    files_json = mock_response_single["files"]._responses[0]._params["json"]
    file_ids = mock_response_single["file_ids"]._responses[0]._params["json"]

    # Include only /README.txt, /data/file1.csv
    file_ids[:] = [files_json[0]["id"], files_json[1]["id"]]
    dataset_json["research_dataset"]["total_files_byte_size"] = sum(
        (f["byte_size"] for f in [files_json[0], files_json[1]])
    )
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    assert list(
        LegacyDataset.objects.get(
            id="c955e904-e3dd-4d7e-99f1-3fed446f96d1"
        ).dataset.file_set.files.values_list("filename", flat=True)
    ) == ["README.txt", "file1.csv"]

    # Include all files
    file_ids[:] = [files_json[0]["id"], files_json[1]["id"], files_json[2]["id"]]
    dataset_json["research_dataset"]["total_files_byte_size"] = sum(
        (f["byte_size"] for f in [files_json[0], files_json[1], files_json[2]])
    )
    call_command(
        "migrate_v2_datasets",
        use_env=True,
        force=True,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
    )
    assert list(
        LegacyDataset.objects.get(
            id="c955e904-e3dd-4d7e-99f1-3fed446f96d1"
        ).dataset.file_set.files.values_list("filename", flat=True)
    ) == ["README.txt", "file1.csv", "file2.csv"]


def test_migrate_command_change_files_metadata(mock_response_single, reference_data, legacy_files):
    def migrate():
        call_command(
            "migrate_v2_datasets",
            identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
            use_env=True,
            force=True,
        )

    # Create files metadata
    migrate()
    dataset = LegacyDataset.objects.get(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1").dataset
    assert list(dataset.file_set.file_metadata.values("file__filename", "title")) == [
        {"file__filename": "README.txt", "title": "Read me"}
    ]

    # Update existing metadata
    dataset_json = mock_response_single["dataset"]._responses[0]._params["json"]
    dataset_json["research_dataset"]["files"][0]["title"] = "Something else"
    migrate()
    assert list(dataset.file_set.file_metadata.values("file__filename", "title")) == [
        {"file__filename": "README.txt", "title": "Something else"}
    ]

    # Delete metadata, create another
    dataset_json["research_dataset"]["files"] = [
        {
            "title": "Some data",
            "description": "File containing data.",
            "file_type": {
                "in_scheme": "http://uri.suomi.fi/codelist/fairdata/file_type",
                "identifier": "http://uri.suomi.fi/codelist/fairdata/file_type/code/text",
                "pref_label": {"en": "Text", "fi": "Teksti", "und": "Teksti"},
            },
            "identifier": "file-2",
            "use_category": {
                "in_scheme": "http://uri.suomi.fi/codelist/fairdata/use_category",
                "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/something",
                "pref_label": {
                    "en": "Something",
                },
            },
            "details": {"id": 2, "file_path": "/data/file1.csv"},
        }
    ]

    migrate()
    assert list(dataset.file_set.file_metadata.values("file__filename", "title")) == [
        {"file__filename": "file1.csv", "title": "Some data"}
    ]


def test_migrate_command_change_directories_metadata(
    mock_response_single, reference_data, legacy_files
):
    def migrate():
        call_command(
            "migrate_v2_datasets",
            identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
            use_env=True,
            force=True,
        )

    # Create directories metadata
    migrate()
    dataset = LegacyDataset.objects.get(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1").dataset
    assert list(dataset.file_set.directory_metadata.values("pathname", "title")) == [
        {"pathname": "/data/", "title": "Run data"}
    ]

    # Update existing metadata
    dataset_json = mock_response_single["dataset"]._responses[0]._params["json"]
    dataset_json["research_dataset"]["directories"][0]["title"] = "Something else"
    migrate()
    assert list(dataset.file_set.directory_metadata.values("pathname", "title")) == [
        {"pathname": "/data/", "title": "Something else"}
    ]

    # Delete metadata
    dataset_json["research_dataset"]["directories"] = []
    migrate()
    assert not dataset.file_set.directory_metadata.exists()


def test_migrate_command_update_wrong_api_version(
    mock_response_single, reference_data, legacy_files
):
    call_command(
        "migrate_v2_datasets",
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    out = StringIO()
    err = StringIO()
    Dataset.objects.filter(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1").update(api_version=3)
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


def test_migrate_command_update_draft(mock_response_draft, reference_data, legacy_files):
    out = StringIO()
    call_command(
        "migrate_v2_datasets",
        stdout=out,
        identifiers=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    output = out.getvalue()
    assert "Processed 1 datasets" in output
    assert Dataset.objects.count() == 1
    assert Dataset.objects.get(id="c955e904-e3dd-4d7e-99f1-3fed446f96d1").state == "draft"


def test_migrate_command_update_file(mock_response_single, reference_data):
    err = StringIO()
    call_command("migrate_v2_datasets", stderr=err, update=True, file="somefile")
    assert "The --file and --update options are mutually exclusive." in err.getvalue().strip()


def test_migrate_missing_args():
    err = StringIO()
    call_command("migrate_v2_datasets", stderr=err)
    assert "Metax instance not specified." in err.getvalue()


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
