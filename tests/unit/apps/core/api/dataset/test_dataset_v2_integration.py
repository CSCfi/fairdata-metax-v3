import logging
import re
from unittest.mock import patch

import pytest
from django.conf import settings as django_settings

from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.sync import V2SyncStatus
from apps.core.services.metax_v2_client import MetaxV2Client

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.django_db(databases=("default", "extra_connection")),
    pytest.mark.dataset,
]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert Dataset.all_objects.count() == 1
    assert requests_mock.call_count == 1
    assert mock_v2_integration["post"].request_history[0].json()["state"] == "published"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_permissions(
    admin_client,
    dataset_a_json,
    mock_v2_integration,
    requests_mock,
    v2_integration_settings,
    enable_sso,
):
    """Test that dataset editors are synced to V2."""
    requests_mock.post(
        f"{django_settings.SSO_HOST}/user_status",
        json={
            "id": "teppo",
            "email": "teppo@example.com",
            "locked": False,
            "modified": "2023-12-14T05:57:11Z",
            "name": "Teppo",
            "qvain_admin_organizations": [],
            "projects": [],
        },
    )

    assert Dataset.all_objects.count() == 0
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    # Add user, username should be added to editor_usernames
    requests_mock.reset_mock()
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/permissions/editors",
        {"username": "teppo"},
        content_type="application/json",
    )
    assert res.status_code == 201
    assert len(mock_v2_integration["put"].request_history) == 1
    assert mock_v2_integration["put"].request_history[0].json()["editor_usernames"] == ["teppo"]

    # Add user, username should be removed from editor_usernames
    requests_mock.reset_mock()
    res = admin_client.delete(
        f"/v3/datasets/{dataset_id}/permissions/editors/teppo", content_type="application/json"
    )
    assert res.status_code == 204
    assert len(mock_v2_integration["put"].request_history) == 1
    assert mock_v2_integration["put"].request_history[0].json()["editor_usernames"] == []


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_draft_dataset_v2_integration(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    # Return 404 to indicate the new dataset is not yet in V2
    mock_get = requests_mock.get(mock_v2_integration["get"]._url, status_code=404)

    # Create draft
    dataset_a_json["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201

    # Update draft
    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"title": {"en": "hello"}}, content_type="application/json"
    )
    assert res.status_code == 200
    assert requests_mock.call_count == 0  # No V2 sync for draft

    # Publish draft
    res = admin_client.post(f"/v3/datasets/{dataset_id}/publish", content_type="application/json")
    assert res.status_code == 200

    assert requests_mock.call_count == 2  # Publication should trigger V2 sync
    assert mock_get.call_count == 1
    assert mock_v2_integration["post"].request_history[0].json()["state"] == "published"


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_versions(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert len(mock_v2_integration["post"].request_history) == 1

    # Return 404 to indicate the new version is not yet in V2
    requests_mock.get(mock_v2_integration["get"]._url, status_code=404)

    dataset_id = res.data["id"]
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/new-version", content_type="application/json"
    )
    assert res.status_code == 201
    assert (
        len(mock_v2_integration["post"].request_history) == 1
    )  # New version is a draft, no v2 sync yet

    version_id = res.data["id"]
    res = admin_client.post(f"/v3/datasets/{version_id}/publish", content_type="application/json")
    assert res.status_code == 200
    assert Dataset.all_objects.count() == 2
    assert len(mock_v2_integration["post"].request_history) == 2
    v2_payload_version_identifiers = (
        mock_v2_integration["post"].request_history[-1].json()["version_identifiers"]
    )
    assert v2_payload_version_identifiers == sorted([dataset_id, version_id])


@pytest.mark.usefixtures("reference_data")
def test_create_legacy_dataset_new_version_v2_integration(
    admin_client,
    mock_v2_integration,
    requests_mock,
    legacy_dataset_a_json,
    data_catalog,
):
    """Test creating a new version from a legacy dataset."""
    # Create legacy dataset
    legacy_dataset_a_json["dataset_json"]["data_catalog"] = {"identifier": data_catalog.id}
    assert Dataset.all_objects.count() == 0
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert len(mock_v2_integration["post"].request_history) == 0

    # Mock 404 for get to indicate the new version is not yet in V2
    requests_mock.get(mock_v2_integration["get"]._url, status_code=404)

    # Create new version of legacy dataset
    dataset_id = res.data["id"]
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/new-version", content_type="application/json"
    )
    assert res.status_code == 201
    assert Dataset.all_objects.count() == 2

    # Original dataset should be marked as a V3 dataset in V2
    assert mock_v2_integration["patch"].call_count == 1
    assert (
        mock_v2_integration["patch"].request_history[0].url
        == f"https://metax-v2-test/rest/v2/datasets/{dataset_id}"
    )
    assert mock_v2_integration["patch"].request_history[0].json() == {
        "identifier": dataset_id,
        "api_meta": {"version": 3},
    }

    # The generate_pid_on_publish field is not yet set for legacy dataset, patch it
    version_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{version_id}",
        {"generate_pid_on_publish": "URN"},
        content_type="application/json",
    )
    assert res.status_code == 200

    # New version is still a draft, no v2 sync yet
    assert len(mock_v2_integration["post"].request_history) == 0

    res = admin_client.post(f"/v3/datasets/{version_id}/publish", content_type="application/json")
    assert res.status_code == 200

    # Dataset is created in V2 after publishing
    assert len(mock_v2_integration["post"].request_history) == 1
    v2_payload_version_identifiers = (
        mock_v2_integration["post"].request_history[-1].json()["version_identifiers"]
    )
    assert v2_payload_version_identifiers == sorted([dataset_id, version_id])


@pytest.mark.usefixtures("reference_data")
def test_create_legacy_draft_dataset_v2_integration(
    admin_client,
    mock_v2_integration,
    requests_mock,
    legacy_dataset_a_json,
    data_catalog,
):
    # Create legacy dataset
    legacy_dataset_a_json["dataset_json"]["data_catalog"] = {"identifier": data_catalog.id}
    legacy_dataset_a_json["dataset_json"]["state"] = "draft"
    assert Dataset.all_objects.count() == 0
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert mock_v2_integration["post"].call_count == 0
    assert mock_v2_integration["patch"].call_count == 0

    # Draft is modified, which should also update its api version in V2
    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"title": {"en": "hello"}}, content_type="application/json"
    )
    assert res.status_code == 200
    assert mock_v2_integration["put"].call_count == 0
    assert mock_v2_integration["patch"].call_count == 1  # Only api_meta is updated
    assert mock_v2_integration["patch"].request_history[0].json() == {
        "identifier": dataset_id,
        "api_meta": {"version": 3},
    }

    # Dataset updated in V2 after publishing
    res = admin_client.post(f"/v3/datasets/{dataset_id}/publish", content_type="application/json")
    assert res.status_code == 200
    assert mock_v2_integration["put"].call_count == 1
    assert mock_v2_integration["put"].request_history[0].json()["state"] == "published"
    assert mock_v2_integration["patch"].call_count == 1
    assert mock_v2_integration["post"].call_count == 0  # No new datasets created


# Run as transactional test so "default" can see commits from "extra connection"
@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_fail(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=400)
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert Dataset.all_objects.count() == 1

    status = V2SyncStatus.objects.get(id=res.data["id"])
    assert status.status == "fail"
    assert status.sync_started is not None
    assert status.sync_files_started is None  # fail before file sync started
    assert status.sync_stopped is not None
    assert "status 400:" in status.error


# Run as transactional test so "default" can see commits from "extra connection"
@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_dataset_v2_integration_status(
    admin_client,
    dataset_a_json,
    mock_v2_integration,
    requests_mock,
    v2_integration_settings,
    monkeypatch,
):
    # Patch update_dataset so we can capture the sync status while sync is running
    incomplete_status = None
    orig_update_dataset = MetaxV2Client.update_dataset

    def patched(*args, **kwargs):
        nonlocal incomplete_status
        incomplete_status = V2SyncStatus.objects.first()
        orig_update_dataset(*args, **kwargs)

    monkeypatch.setattr(MetaxV2Client, "update_dataset", patched)

    assert Dataset.all_objects.count() == 0
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert requests_mock.call_count == 1

    # Check that status showed as incomplete when update was ongoing
    assert incomplete_status.status == "incomplete"
    assert incomplete_status.sync_stopped is None
    assert incomplete_status.error is None

    # Check that status shows as success after sync is done
    status = V2SyncStatus.objects.get(id=res.data["id"])
    assert status.status == "success"
    assert status.sync_started == incomplete_status.sync_started
    assert status.sync_started is not None
    assert status.sync_stopped is not None
    assert status.error is None


@pytest.fixture
def mock_tasks():
    """Make run_task to collect tasks in list instead of running them directlyF."""
    tasks = []

    def impl(fn, *args, **kwargs):
        tasks.append(lambda: fn(*args, **kwargs))

    with patch("apps.core.signals.run_task", impl):
        yield tasks


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_dataset_v2_integration_tasks_in_order(
    admin_client,
    dataset_a_json,
    mock_v2_integration,
    requests_mock,
    mock_tasks,
    v2_integration_settings,
):
    """Test running sync-to-V2 tasks in order."""
    # Create and patch dataset, should trigger two sync tasks
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"title": {"en": "new title"}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert len(mock_tasks) == 2

    # Sync create
    mock_tasks[0]()
    assert requests_mock.call_count == 1
    assert requests_mock.request_history[0].method == "POST"

    # Sync update
    mock_tasks[1]()
    assert requests_mock.call_count == 3
    assert requests_mock.request_history[1].method == "GET"
    assert requests_mock.request_history[2].method == "PUT"
    assert requests_mock.request_history[2].json()["research_dataset"]["title"] == {
        "en": "new title"
    }


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_dataset_v2_integration_tasks_out_of_order(
    admin_client,
    dataset_a_json,
    mock_v2_integration,
    requests_mock,
    mock_tasks,
    v2_integration_settings,
):
    """Test running sync-to-V2 tasks in reverse order."""
    # Return 404 from GET /v3/datasest/<id>
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("GET", matcher, status_code=404),

    # Create and patch dataset, should trigger two sync tasks
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"title": {"en": "new title"}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert len(mock_tasks) == 2

    # Sync update before create
    mock_tasks[1]()
    assert requests_mock.call_count == 2
    assert requests_mock.request_history[0].method == "GET"
    assert requests_mock.request_history[1].method == "POST"
    assert requests_mock.request_history[1].json()["research_dataset"]["title"] == {
        "en": "new title"
    }

    # Sync create, should not make new requests because a later version has already been synced
    mock_tasks[0]()
    assert requests_mock.call_count == 2


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_patch_actors(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    """Ensure patching dataset updates actors in V2."""
    assert Dataset.all_objects.count() == 0
    dataset_a_json["provenance"] = [
        {
            "title": {"en": "Collection"},
            "is_associated_with": [
                {
                    "person": {"name": "prov person"},
                    "organization": {"pref_label": {"en": "prov org"}},
                }
            ],
        },
    ]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert Dataset.all_objects.count() == 1
    assert requests_mock.call_count == 1
    research_dataset = mock_v2_integration["post"].request_history[0].json()["research_dataset"]
    assert research_dataset["creator"] == [
        {
            "@type": "Organization",
            "name": {
                "en": "test org",
            },
        },
    ]

    # Update dataset actors
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {
            "actors": [
                {
                    "person": {"name": "test person"},
                    "organization": {"pref_label": {"en": "test org"}},
                    "roles": ["creator", "publisher"],
                }
            ],
            "provenance": [
                {
                    "title": {"en": "New collection"},
                    "is_associated_with": [
                        {
                            "person": {"name": "prov person with new name"},
                            "organization": {"pref_label": {"en": "prov org"}},
                        }
                    ],
                },
            ],
        },
        content_type="application/json",
    )
    assert res.status_code == 200
    assert requests_mock.call_count == 3

    # Check the payload contains updated actors and provenance
    research_dataset = mock_v2_integration["put"].request_history[0].json()["research_dataset"]
    assert research_dataset["creator"] == [
        {
            "name": "test person",
            "@type": "Person",
            "member_of": {"@type": "Organization", "name": {"en": "test org"}},
        }
    ]
    research_dataset = mock_v2_integration["put"].request_history[0].json()["research_dataset"]
    assert research_dataset["provenance"][0]["title"]["en"] == "New collection"
    assert (
        research_dataset["provenance"][0]["was_associated_with"][0]["name"]
        == "prov person with new name"
    )
