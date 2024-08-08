import re

import pytest
from django.db.models import F
from django.utils.dateparse import parse_datetime
from tests.utils import matchers
from tests.utils.utils import assert_same_datetime

from apps.files.models.file import File

pytestmark = [pytest.mark.django_db, pytest.mark.adapter]


class V2SyncMock:
    next_id = 1

    def callback(self, request, context):
        files = request.json()

        output = []
        for file in files:
            out_file = {
                "identifier": file["identifier"],
                "id": file["id"],
                "file_storage": file["file_storage"],
            }
            if out_file["id"] is None:
                out_file["id"] = self.next_id
                self.next_id += 1
            output.append(out_file)

        context.status_code = 200
        return output


@pytest.fixture
def mock_v2_files_integration(requests_mock, v2_integration_settings):
    host = v2_integration_settings.METAX_V2_HOST
    syncmock = V2SyncMock()
    return {
        "sync_mock": requests_mock.post(
            f"{host}/rest/v2/files/sync_from_v3", json=syncmock.callback
        )
    }


def get_file_json(name):
    return {
        "storage_identifier": f"file_{name}",
        "pathname": f"/data/{name}",
        "csc_project": "fd_test_project",
        "storage_service": "ida",
        "size": 1024,
        "checksum": "md5:bd0f1dff407071e5db8eb57dde4847a3",
        "frozen": "2022-11-12T11:20:01Z",
        "modified": "2022-11-12T10:34:00Z",
        "user": "fd_user",
    }


def get_file_output_json(name, removed=None):
    return {
        "id": None,
        "identifier": f"file_{name}",
        "file_path": f"/data/{name}",
        "file_uploaded": "2022-11-12T10:34:00Z",
        "file_modified": "2022-11-12T10:34:00Z",
        "file_frozen": "2022-11-12T11:20:01Z",
        "byte_size": 1024,
        "file_storage": "urn:nbn:fi:att:file-storage-ida",
        "project_identifier": "fd_test_project",
        "user_modified": "fd_user",
        "date_created": matchers.DateTimeStr(),
        "date_modified": matchers.DateTimeStr(),
        "date_removed": removed,
        "file_deleted": removed,
        "removed": bool(removed),
        "checksum_checked": "2022-11-12T10:34:00Z",
        "checksum_algorithm": "MD5",
        "checksum_value": "bd0f1dff407071e5db8eb57dde4847a3",
    }


def test_sync_create_file(admin_client, mock_v2_files_integration):
    file = get_file_json(name="testfile1.txt")
    res = admin_client.post("/v3/files", file, content_type="application/json")
    assert res.status_code == 201
    assert mock_v2_files_integration["sync_mock"].call_count == 1

    # Check id created by V2 mock has been assigned to file
    file = File.objects.get(id=res.data["id"])
    assert file.legacy_id == 1
    assert file.storage_service == "ida"


def test_sync_update_file(admin_client, mock_v2_files_integration):
    file = get_file_json(name="testfile1.txt")
    res = admin_client.post("/v3/files", file, content_type="application/json")
    assert res.status_code == 201

    res = admin_client.patch(
        f"/v3/files/{res.data['id']}", {"size": 2048}, content_type="application/json"
    )
    assert res.status_code == 200
    sync_mock = mock_v2_files_integration["sync_mock"]
    assert sync_mock.call_count == 2
    assert sync_mock.request_history[0].json()[0]["id"] is None
    assert sync_mock.request_history[0].json()[0] == get_file_output_json(name="testfile1.txt")
    assert sync_mock.request_history[1].json()[0]["id"] == 1

    # Check id created by V2 mock has been assigned to file
    file = File.objects.get(id=res.data["id"])
    assert file.legacy_id == 1


def test_sync_delete_file(admin_client, mock_v2_files_integration):
    file = get_file_json(name="testfile1.txt")
    res = admin_client.post("/v3/files", file, content_type="application/json")
    assert res.status_code == 201

    file_id = res.data["id"]
    res = admin_client.delete(
        f"/v3/files/{file_id}", {"size": 2048}, content_type="application/json"
    )
    assert res.status_code == 204
    sync_mock = mock_v2_files_integration["sync_mock"]
    assert sync_mock.call_count == 2
    assert sync_mock.request_history[0].json()[0]["id"] is None
    assert sync_mock.request_history[1].json()[0]["id"] == 1

    # Check id created by V2 mock has been assigned to file
    file = File.all_objects.get(id=file_id)
    assert file.legacy_id == 1


def test_sync_update_file_missing_from_v2(
    admin_client, v2_integration_settings, mock_v2_files_integration
):
    # Create file that has legacy_id but is not in associated V2 instance
    sync_mock = mock_v2_files_integration["sync_mock"]
    v2_integration_settings.METAX_V2_INTEGRATION_ENABLED = False
    file = get_file_json(name="testfile1.txt")
    res = admin_client.post("/v3/files", file, content_type="application/json")
    assert res.status_code == 201
    assert sync_mock.call_count == 0
    file_id = res.data["id"]
    File.all_objects.filter(id=file_id).update(legacy_id=5123)

    # V2 respects id provided by V3
    v2_integration_settings.METAX_V2_INTEGRATION_ENABLED = True
    res = admin_client.patch(
        f"/v3/files/{res.data['id']}", {"size": 2048}, content_type="application/json"
    )
    assert res.status_code == 200
    assert sync_mock.call_count == 1
    assert sync_mock.request_history[0].json()[0]["id"] == 5123

    # Check id has not changed
    file = File.objects.get(id=file_id)
    assert file.legacy_id == 5123


def test_sync_batch_create_file(admin_client, mock_v2_files_integration):
    files = [get_file_json(name="testfile1.txt"), get_file_json(name="testfile2.txt")]
    res = admin_client.post("/v3/files/put-many", files, content_type="application/json")
    assert res.status_code == 200
    assert mock_v2_files_integration["sync_mock"].call_count == 1

    # Check id created by V2 mock has been assigned to file
    file = File.objects.filter(id__in=[f["object"]["id"] for f in res.data["success"]]).values(
        "legacy_id", "filename", service=F("storage__storage_service")
    )
    assert list(file) == [
        {"legacy_id": 1, "filename": "testfile1.txt", "service": "ida"},
        {"legacy_id": 2, "filename": "testfile2.txt", "service": "ida"},
    ]


def test_sync_batch_remove_files(admin_client, mock_v2_files_integration):
    files = [get_file_json(name="testfile1.txt"), get_file_json(name="testfile2.txt")]
    res = admin_client.post("/v3/files/put-many", files, content_type="application/json")
    assert res.status_code == 200

    res = admin_client.post("/v3/files/delete-many", files, content_type="application/json")
    assert res.status_code == 200
    assert mock_v2_files_integration["sync_mock"].call_count == 2

    # Check that files were marked as removed with correct timestamps
    removed = File.all_objects.get(filename="testfile1.txt").removed.isoformat()
    post_data = mock_v2_files_integration["sync_mock"].request_history[1].json()
    assert post_data[0]["identifier"] == "file_testfile1.txt"
    assert post_data[0]["removed"] == True
    assert_same_datetime(post_data[0]["date_removed"], removed)
    assert_same_datetime(post_data[0]["file_deleted"], removed)

    removed = File.all_objects.get(filename="testfile2.txt").removed.isoformat()
    assert post_data[1]["identifier"] == "file_testfile2.txt"
    assert post_data[1]["removed"] == True
    assert_same_datetime(post_data[1]["date_removed"], removed)
    assert_same_datetime(post_data[1]["file_deleted"], removed)
