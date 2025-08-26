import pytest
from django.utils import timezone
from rest_framework.reverse import reverse

from apps.core.models.catalog_record.dataset import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.adapter]


def create_editor_json(user_id, modified=None, removed=False):
    if not modified:
        modified = timezone.now().isoformat()
    return {
        "id": "4f576de4-74e7-4a8c-b4e5-3c838b56b0f9",
        "active": True,
        "removed": removed,
        "date_modified": modified,
        "user_modified": None,
        "date_created": "2020-01-02T03:04:05+03:00",
        "user_created": None,
        "service_modified": None,
        "service_created": None,
        "date_removed": modified if removed else None,
        "user_id": user_id,
        "role": "editor",
        "editor_permissions": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
    }


def test_update_editors(
    admin_client, data_catalog_att, legacy_dataset_a_json, license_reference_data
):
    """Test updating editors in legacy dataset."""
    dataset_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    legacy_dataset_a_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_1")],
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    # Add new editor to dataset json
    legacy_dataset_a_json["dataset_json"]["editor_permissions"]["users"].append(
        create_editor_json("editor_2")
    )
    res = admin_client.patch(
        reverse("migrated-dataset-detail", kwargs={"pk": dataset_id}),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.get(
        reverse("dataset-permissions-detail", kwargs={"dataset_pk": dataset_id}),
        content_type="application/json",
    )
    assert [user["username"] for user in res.data["editors"]] == ["editor_1", "editor_2"]


def test_create_legacy_datasets_with_shared_permissions(
    admin_client,
    data_catalog_att,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    license_reference_data,
):
    """Test creating multiple legacy datasets that share the same EditorPermissions instance."""
    legacy_dataset_a_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_user")],
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    dataset_a_id = res.data["id"]

    # Create legacy dataset b sharing same permissions object as dataset a. Added
    # editor user should then be in both datasets.
    legacy_dataset_b_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_user"), create_editor_json("another_editor_user")],
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    dataset_b_id = res.data["id"]

    assert (
        Dataset.objects.get(id=dataset_a_id).permissions_id
        == Dataset.objects.get(id=dataset_b_id).permissions_id
    )

    # Check dataset a editors
    res = admin_client.get(
        reverse("dataset-permissions-detail", kwargs={"dataset_pk": dataset_a_id}),
        content_type="application/json",
    )
    assert [user["username"] for user in res.data["editors"]] == [
        "another_editor_user",
        "editor_user",
    ]

    # Check dataset b editors
    res = admin_client.get(
        reverse("dataset-permissions-detail", kwargs={"dataset_pk": dataset_b_id}),
        content_type="application/json",
    )
    assert [user["username"] for user in res.data["editors"]] == [
        "another_editor_user",
        "editor_user",
    ]


def test_remove_editor(
    admin_client, data_catalog_att, legacy_dataset_a_json, license_reference_data
):
    """Test removing an editor from a legacy dataset."""
    dataset_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    legacy_dataset_a_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_1")],
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    # Remove editor, add another
    legacy_dataset_a_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_1", removed=True), create_editor_json("editor_2")],
    }
    res = admin_client.patch(
        reverse("migrated-dataset-detail", kwargs={"pk": dataset_id}),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    res = admin_client.get(
        reverse("dataset-permissions-detail", kwargs={"dataset_pk": dataset_id}),
        content_type="application/json",
    )
    assert [user["username"] for user in res.data["editors"]] == ["editor_2"]


def test_ignore_previously_added_editor(
    admin_client, data_catalog_att, legacy_dataset_a_json, license_reference_data
):
    """Test that only changes newer than DatasetPermissions.legacy_modified are applied."""
    dataset_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    legacy_dataset_a_json["dataset_json"]["editor_permissions"] = {
        "id": "4efd0669-33d4-4feb-93fb-5372d0f93a92",
        "users": [create_editor_json("editor_1")],
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201

    # Editor "previously_added_editor" has been added before current
    # legacy_modified timestamp in DatasetPermissions, so it should be ignored
    legacy_dataset_a_json["dataset_json"]["editor_permissions"]["users"].append(
        create_editor_json(
            "previously_added_editor", modified=timezone.now() - timezone.timedelta(days=1)
        )
    )
    res = admin_client.patch(
        reverse("migrated-dataset-detail", kwargs={"pk": dataset_id}),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    res = admin_client.get(
        reverse("dataset-permissions-detail", kwargs={"dataset_pk": dataset_id}),
        content_type="application/json",
    )
    assert [user["username"] for user in res.data["editors"]] == ["editor_1"]


def test_legacy_dataset_list_permissions(
    user_client, user2_client, appsupport_client, client, legacy_dataset_a
):
    url = reverse("migrated-dataset-list")
    res = user_client.get(url, content_type="application/json")
    assert res.status_code == 200
    assert len(res.data["results"]) == 1  # User has one migrated dataset

    res = appsupport_client.get(url, content_type="application/json")
    assert res.status_code == 200
    assert len(res.data["results"]) == 1  # Appsupport user sees all migrated datasets

    res = user2_client.get(url, content_type="application/json")
    assert res.status_code == 200
    assert len(res.data["results"]) == 0  # User has no migrated datasets

    res = client.get(url, content_type="application/json")
    assert res.status_code == 403  # User is not authenticated


def test_legacy_dataset_retrieve_permissions(
    user_client, user2_client, appsupport_client, client, legacy_dataset_a
):
    dataset_id = legacy_dataset_a.data["id"]
    url = reverse("migrated-dataset-detail", args=[dataset_id])
    res = user_client.get(url, content_type="application/json")
    assert res.status_code == 200
    assert res.data["id"] == dataset_id  # User sees their own migrated dataset

    res = appsupport_client.get(url, content_type="application/json")
    assert res.status_code == 200
    assert res.data["id"] == dataset_id  # Appsupport user sees all migrated datasets

    res = user2_client.get(url, content_type="application/json")
    assert res.status_code == 404  # User no access to migrated dataset by other users

    res = client.get(url, content_type="application/json")
    assert res.status_code == 403  # User is not authenticated
