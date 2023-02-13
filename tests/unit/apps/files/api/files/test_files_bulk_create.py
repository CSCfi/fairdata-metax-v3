import pytest

from apps.files import factories
from apps.files.serializers import FileSerializer


@pytest.mark.django_db
def test_files_create_bulk(client, ida_file_json):
    project = factories.StorageProjectFactory(
        project_identifier="project_x",
        file_storage__id="ida",
    )
    files = [
        FileSerializer(factories.FileFactory.build(storage_project=project)).data,
        FileSerializer(factories.FileFactory.build(storage_project=project)).data,
        FileSerializer(factories.FileFactory.build(storage_project=project)).data,
        FileSerializer(factories.FileFactory.build(storage_project=project)).data,
        FileSerializer(factories.FileFactory.build(storage_project=project)).data,
    ]
    res = client.post(
        "/rest/v3/files",
        files,
        content_type="application/json",
    )
    assert res.status_code == 201
    file_paths = {f["file_path"] for f in files}
    assert {f["file_path"] for f in res.json()} == file_paths


@pytest.fixture
def files_some_already_exist():
    project = factories.StorageProjectFactory(
        project_identifier="project_x",
        file_storage__id="ida",
    )
    files = [
        FileSerializer(
            factories.FileFactory.create(storage_project=project)
        ).data,  # already created
        FileSerializer(
            factories.FileFactory.create(storage_project=project)
        ).data,  # already created
        FileSerializer(
            factories.FileFactory.build(storage_project=project)
        ).data,  # new file
    ]
    return files


@pytest.mark.django_db
def test_files_create_bulk_error_some_files_already_exist(
    client, files_some_already_exist
):
    res = client.post(
        "/rest/v3/files",
        files_some_already_exist,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "file_path" in res.data


@pytest.mark.django_db
def test_files_create_bulk_ignore_already_exists_errors(
    client, files_some_already_exist
):
    res = client.post(
        "/rest/v3/files?ignore_already_exists_errors=true",
        files_some_already_exist,
        content_type="application/json",
    )
    assert res.status_code == 201
    assert len(res.data) == 1  # only non-conflicting files are returned
    assert res.data[0]["file_name"] == files_some_already_exist[2]["file_name"]
