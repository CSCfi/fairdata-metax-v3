import logging
import re

import pytest
from django.conf import settings as django_settings

from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


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


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_v2_integration_fail(
    admin_client, dataset_a_json, mock_v2_integration, requests_mock, v2_integration_settings
):
    assert Dataset.all_objects.count() == 0
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    requests_mock.register_uri("POST", matcher, status_code=400)
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 409
    assert Dataset.all_objects.count() == 0
