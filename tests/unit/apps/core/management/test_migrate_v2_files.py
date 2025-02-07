from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.exceptions import ValidationError

from apps.files.factories import create_v2_file_data
from apps.files.models import File
from apps.refdata.models import FileFormatVersion

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.adapter,
    pytest.mark.usefixtures("data_catalog", "reference_data", "v2_integration_settings"),
]


def fake_files_endpoint(projects, overrides=None):
    files = create_v2_file_data(projects, overrides)

    def callback(request, context):
        query = request.qs
        filtered = [*files]
        if query.get("removed") == ["true"]:
            filtered = [f for f in filtered if f.get("removed")]
        else:
            filtered = [f for f in filtered if not f.get("removed")]

        if storage := query.get("file_storage"):
            filtered = [f for f in filtered if f["file_storage"]["identifier"] == storage[0]]
        if project := query.get("project_identifier"):
            filtered = [f for f in filtered if f["project_identifier"] == project[0]]
        if id__gt := query.get("id__gt"):
            filtered = [f for f in filtered if f["id"] > int(id__gt[0])]

        limit = int((query.get("limit") or [10])[0])
        offset = int((query.get("offset") or [0])[0])
        paginated = filtered[offset : limit + offset]

        next_link = None
        if offset + limit < len(filtered):
            next_query_dict = {**query, "offset": [offset + limit], "limit": [limit]}
            next_query = "&".join(f"{k}={v[0]}" for k, v in next_query_dict.items())
            next_link = f"https://metax-v2-test/rest/v2/files?{next_query}"

        context.status_code = 200
        return {"count": len(filtered), "results": paginated, "next": next_link}

    return callback


@pytest.fixture
def mock_endpoint_files(requests_mock):
    return requests_mock.get(
        url="https://metax-v2-test/rest/v2/files",
        json=fake_files_endpoint(
            {
                "ida:project_x": [
                    "/data/file1",
                    "/data/file2",
                    "/data/file3",
                ],
                "pas:project_y": [
                    "/readme.md",
                    "/license.txt",
                ],
                "pas:project_z": ["/dir1/y1.txt", "/dir1/y2.txt", "-/dir1/y3.txt", "/dir2/z.txt"],
            },
        ),
    )


@pytest.fixture
def mock_endpoint_files_characteristics(requests_mock):
    return requests_mock.get(
        url="https://metax-v2-test/rest/v2/files",
        json=fake_files_endpoint(
            {
                "ida:project_x": [
                    "/data/file1",
                    "/data/file2",
                    "/data/file3",
                ],
            },
            overrides={
                "file_characteristics": {
                    "encoding": "UTF-8",
                    "file_format": "application/pdf",
                    "format_version": "1.2",
                    "csv_delimiter": "|",
                    "csv_has_header": True,
                    "csv_quoting_char": "\\",
                    "csv_record_separator": "LF",
                },
                "file_characteristics_extension": {"some_data": "ok"},
            },
        ),
    )


@pytest.fixture
def mock_endpoint_files_characteristics_invalid_format(requests_mock):
    return requests_mock.get(
        url="https://metax-v2-test/rest/v2/files",
        json=fake_files_endpoint(
            {
                "ida:project_x": [
                    "/data/file1",
                    "/data/file2",
                    "/data/file3",
                ],
            },
            overrides={
                "file_characteristics": {
                    "file_format": "application/peedeeäf",
                    "format_version": "1.2234",
                }
            },
        ),
    )


def test_migrate_command(mock_response, mock_endpoint_files):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True)
    assert [
        (f.storage.storage_service, f.storage.csc_project, f.pathname, bool(f.removed))
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("ida", "project_x", "/data/file1", False),
        ("ida", "project_x", "/data/file2", False),
        ("ida", "project_x", "/data/file3", False),
        ("pas", "project_y", "/readme.md", False),
        ("pas", "project_y", "/license.txt", False),
        ("pas", "project_z", "/dir1/y1.txt", False),
        ("pas", "project_z", "/dir1/y2.txt", False),
        ("pas", "project_z", "/dir1/y3.txt", True),
        ("pas", "project_z", "/dir2/z.txt", False),
    ]
    assert len(err.readlines()) == 0
    assert mock_endpoint_files.call_count == 2  # not removed + removed


def test_migrate_command_characteristics(mock_response, mock_endpoint_files_characteristics):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True)
    f = File.all_objects.first()
    assert (
        f.characteristics.file_format_version.url
        == "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
    )
    assert f.characteristics_extension == {"some_data": "ok"}
    assert f.characteristics.encoding == "UTF-8"
    assert f.characteristics.csv_has_header == True
    assert f.characteristics.csv_delimiter == "|"
    assert f.characteristics.csv_quoting_char == "\\"
    assert f.characteristics.csv_record_separator == "LF"
    file_id = f.id
    characteristics_id = f.characteristics.id

    # Change record separator, migration should revert it
    f.characteristics.csv_record_separator = "CR"
    f.characteristics.save()

    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True)
    f = File.all_objects.get(id=file_id)
    assert f.characteristics.csv_record_separator == "LF"
    assert f.characteristics.id == characteristics_id

    # Change file format version, migration should revert it
    f.characteristics.file_format_version = FileFormatVersion.objects.get(file_format="text/csv")
    f.characteristics.save()

    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True)
    f = File.all_objects.get(id=file_id)
    assert (
        f.characteristics.file_format_version.url
        == "http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2"
    )
    assert f.characteristics.id == characteristics_id


def test_migrate_command_characteristics_invalid_format(
    mock_response, mock_endpoint_files_characteristics_invalid_format
):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True, allow_fail=True)
    assert (
        "File legacy_id=1 format version not found file_format='application/peedeeäf'"
        in err.getvalue()
    )
    assert "processed=3, created=3, updated=0, errors=3" in out.getvalue()

    with pytest.raises(ValidationError):
        call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True, allow_fail=False)


def test_migrate_command_modified_since(mock_response, mock_endpoint_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_files",
        stdout=out,
        stderr=err,
        use_env=True,
        modified_since="2024-08-09T12:34:56+03:00",
    )
    assert File.all_objects.count() == 9
    assert len(err.readlines()) == 0
    assert mock_endpoint_files.call_count == 2  # not removed + removed
    history = mock_endpoint_files.request_history
    assert history[0].headers.get("If-Modified-Since") == "Fri, 09 Aug 2024 09:34:56 GMT"
    assert history[1].headers.get("If-Modified-Since") == "Fri, 09 Aug 2024 09:34:56 GMT"


def test_migrate_command_update(mock_response, mock_endpoint_files):
    # Do initial migration
    out = StringIO()
    call_command("migrate_v2_files", use_env=True, stdout=out)
    assert File.all_objects.count() == 9
    assert "processed=9, created=9, updated=0" in out.getvalue()

    # Edit files
    File.all_objects.get(filename="file1").delete(soft=False)  # hard delete
    File.objects.get(filename="readme.md").delete()  # soft delete
    assert File.all_objects.filter(directory_path="/dir1/").update(size=123) == 3
    assert File.all_objects.count() == 8
    assert list(
        File.all_objects.filter(directory_path="/dir1/").values_list("size", flat=True)
    ) == [123, 123, 123]

    # Files should revert to old values when updated
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_files", use_env=True, stdout=out, stderr=err)
    assert "processed=9, created=1, updated=4" in out.getvalue()
    assert [
        (f.storage.storage_service, f.storage.csc_project, f.pathname, bool(f.removed))
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("ida", "project_x", "/data/file1", False),
        ("ida", "project_x", "/data/file2", False),
        ("ida", "project_x", "/data/file3", False),
        ("pas", "project_y", "/readme.md", False),
        ("pas", "project_y", "/license.txt", False),
        ("pas", "project_z", "/dir1/y1.txt", False),
        ("pas", "project_z", "/dir1/y2.txt", False),
        ("pas", "project_z", "/dir1/y3.txt", True),
        ("pas", "project_z", "/dir2/z.txt", False),
    ]
    assert list(
        File.all_objects.filter(directory_path="/dir1/").values_list("size", flat=True)
    ) == [
        1000,
        1000,
        1000,
    ]


def test_migrate_command_paginated(mock_response, mock_endpoint_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_files",
        stdout=out,
        stderr=err,
        use_env=True,
        pagination_size=3,
    )
    assert [f.pathname for f in File.all_objects.order_by("legacy_id").all()] == [
        "/data/file1",
        "/data/file2",
        "/data/file3",
        "/readme.md",
        "/license.txt",
        "/dir1/y1.txt",
        "/dir1/y2.txt",
        "/dir1/y3.txt",
        "/dir2/z.txt",
    ]
    assert mock_endpoint_files.call_count == 4  # 3x not removed + 1x removed


def test_migrate_dataset_files(mock_response_single, mock_response_dataset_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_files",
        stdout=out,
        stderr=err,
        datasets=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        use_env=True,
    )
    assert File.all_objects.count() == 3


def test_migrate_data_catalog_files(mock_response_single_catalog, mock_response_dataset_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_files",
        stdout=out,
        stderr=err,
        datasets_from_catalogs=["urn:nbn:fi:att:data-catalog-ida"],
        use_env=True,
    )
    assert File.all_objects.count() == 3


def test_migrate_storage_files(mock_endpoint_files):
    out = StringIO()
    err = StringIO()
    call_command(
        "migrate_v2_files",
        stdout=out,
        stderr=err,
        storages=["pas"],
        use_env=True,
    )
    assert [
        (f.storage.storage_service, f.pathname)
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("pas", "/readme.md"),
        ("pas", "/license.txt"),
        ("pas", "/dir1/y1.txt"),
        ("pas", "/dir1/y2.txt"),
        ("pas", "/dir1/y3.txt"),
        ("pas", "/dir2/z.txt"),
    ]


def test_migrate_projects(mock_endpoint_files):
    call_command(
        "migrate_v2_files",
        projects=["project_x"],
        use_env=True,
    )
    assert [
        (f.storage.storage_service, f.storage.csc_project, f.pathname, bool(f.removed))
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("ida", "project_x", "/data/file1", False),
        ("ida", "project_x", "/data/file2", False),
        ("ida", "project_x", "/data/file3", False),
    ]


def test_migrate_file_offset(mock_response, mock_endpoint_files):
    """Test migrating files with offset and project prefix."""
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_files", stdout=out, stderr=err, use_env=True, file_offset=100000000)
    assert [
        (f.storage.storage_service, f.storage.csc_project, f.pathname, bool(f.removed))
        for f in File.all_objects.order_by("legacy_id").all()
    ] == [
        ("ida", "100000000-project_x", "/data/file1", False),
        ("ida", "100000000-project_x", "/data/file2", False),
        ("ida", "100000000-project_x", "/data/file3", False),
        ("pas", "100000000-project_y", "/readme.md", False),
        ("pas", "100000000-project_y", "/license.txt", False),
        ("pas", "100000000-project_z", "/dir1/y1.txt", False),
        ("pas", "100000000-project_z", "/dir1/y2.txt", False),
        ("pas", "100000000-project_z", "/dir1/y3.txt", True),
        ("pas", "100000000-project_z", "/dir2/z.txt", False),
    ]
    assert all(
        [
            (f.legacy_id > 100000000) and f.storage_identifier.startswith("100000000-")
            for f in File.all_objects.order_by("legacy_id").all()
        ]
    )
    assert len(err.readlines()) == 0
    assert mock_endpoint_files.call_count == 2  # not removed + removed


def test_migrate_missing_config():
    err = StringIO()
    call_command("migrate_v2_files", stderr=err)
    assert "Missing Metax V2 configuration" in err.getvalue()


def test_migrate_invalid_args():
    err = StringIO()
    call_command("migrate_v2_files", stderr=err, projects=["x"], datasets=["y"])
    assert (
        "projects, storages, and modified-since arguments are not supported with datasets"
        in err.getvalue()
    )


def test_migrate_dataset_error(requests_mock):
    requests_mock.get(
        url="https://metax-v2-test/rest/v2/datasets/xyz",
        status_code=403,
        json={"detail": "Not allowed"},
    )
    err = StringIO()
    call_command("migrate_v2_files", stderr=err, use_env=True, allow_fail=True, datasets=["xyz"])
    assert "Error for dataset xyz" in err.getvalue()
