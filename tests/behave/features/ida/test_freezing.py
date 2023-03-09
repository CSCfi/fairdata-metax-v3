import logging
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone
from pytest_bdd import scenario, then, when
from rest_framework.reverse import reverse

from apps.core import factories
from apps.files.models import StorageProject

logger = logging.getLogger(__name__)


@pytest.fixture
def project_identifier():
    return "project_x"


@pytest.fixture
def files_json(ida_file_storage, project_identifier):
    return [
        {
            "file_path": "/data/1.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "file_storage": ida_file_storage.id,
            "byte_size": 1024,
            "checksum": {
                "value": "123",
                "algorithm": "MD5",
                "checked": "2022-11-13T12:34:00Z",
            },
        },
        {
            "file_path": "/data/2.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "file_storage": ida_file_storage.id,
            "byte_size": 1024,
            "checksum": {
                "value": "123",
                "algorithm": "MD5",
                "checked": "2022-11-13T12:34:00Z",
            },
        },
        {
            "file_path": "/data/3.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "file_storage": ida_file_storage.id,
            "byte_size": 1024,
            "checksum": {
                "value": "123",
                "algorithm": "MD5",
                "checked": "2022-11-13T12:34:00Z",
            },
        },
    ]


@when("user freezes new files in IDA", target_fixture="file_response")
def post_ida_file(admin_client, files_json):
    """

    TODO:
        * should be replaced with real request object when Files-API is ready

    Returns: Mocked request object

    """

    url = reverse("files-list")
    return admin_client.post(url, files_json, content_type="application/json")


@then("a new storage project is created", target_fixture="created_storage_project")
def created_storage_project(ida_file_storage, project_identifier) -> StorageProject:
    """

    Args:
        ida_file_storage (FileStorage): FileStorage instance

    Returns:
        StorageProject: Dataset StorageProject

    """
    return StorageProject.available_objects.get(
        file_storage=ida_file_storage, project_identifier=project_identifier
    )


@then("the storage project has the files associated with it")
def storage_project(created_storage_project, files_json) -> StorageProject:
    """Ensure files are associated with the storage project

    Args:
        created_storage_project (StorageProject): StorageProject from freezing action on IDA

    Returns:
        StorageProject: StorageProject with files

    """
    file_paths = set(f["file_path"] for f in files_json)
    created_paths = set(f.file_path for f in created_storage_project.files.all())
    assert created_paths == file_paths


@then("API returns OK status")
def files_ok_response(file_response):
    """

    Args:
        file_response (): response to POST from IDA to Files API

    Returns:

    """
    assert file_response.status_code == 201


@scenario("file.feature", "IDA User freezes files")
def test_file_freeze():
    pass
