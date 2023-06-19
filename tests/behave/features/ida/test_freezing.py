import logging
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone
from pytest_bdd import scenario, then, when
from rest_framework.reverse import reverse

from apps.core import factories
from apps.files.models import FileStorage

logger = logging.getLogger(__name__)


@pytest.fixture
def project_identifier():
    return "project_x"


@pytest.fixture
def files_json(project_identifier):
    return [
        {
            "file_storage_identifier": "ida-file-1",
            "file_path": "/data/1.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "storage_service": "ida",
            "byte_size": 1024,
            "checksum": {
                "value": "123",
                "algorithm": "MD5",
                "checked": "2022-11-13T12:34:00Z",
            },
        },
        {
            "file_storage_identifier": "ida-file-2",
            "file_path": "/data/2.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "storage_service": "ida",
            "byte_size": 1024,
            "checksum": {
                "value": "123",
                "algorithm": "MD5",
                "checked": "2022-11-13T12:34:00Z",
            },
        },
        {
            "file_storage_identifier": "ida-file-3",
            "file_path": "/data/3.csv",
            "date_uploaded": "2022-11-13T12:34:00Z",
            "file_modified": "2022-11-13T12:34:00Z",
            "project_identifier": project_identifier,
            "storage_service": "ida",
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

    url = reverse("file-insert-many")
    return admin_client.post(url, files_json, content_type="application/json")


@then("a new file storage is created", target_fixture="created_file_storage")
def created_file_storage(project_identifier) -> FileStorage:
    """

    Args:
        ida_file_storage (FileStorage): FileStorage instance

    Returns:
        FileStorage: Dataset FileStorage

    """
    return FileStorage.available_objects.get(
        storage_service="ida", project_identifier=project_identifier
    )


@then("the file storage has the files associated with it")
def file_storage(created_file_storage, files_json) -> FileStorage:
    """Ensure files are associated with the storage project

    Args:
        created_file_storage (FileStorage): FileStorage from freezing action on IDA

    Returns:
        FileStorage: FileStorage with files

    """
    file_paths = set(f["file_path"] for f in files_json)
    created_paths = set(f.file_path for f in created_file_storage.files.all())
    assert created_paths == file_paths


@then("API returns OK status")
def files_ok_response(file_response):
    """

    Args:
        file_response (): response to POST from IDA to Files API

    Returns:

    """
    assert file_response.status_code == 200


@scenario("file.feature", "IDA User freezes files")
def test_file_freeze():
    pass
