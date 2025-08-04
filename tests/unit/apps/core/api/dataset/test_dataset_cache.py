import logging
from datetime import timedelta

import pytest
from django.utils import timezone
from tests.utils import matchers

from apps.common.serializers.fields import PrivateEmailValue

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset_in_cache(dataset_cache, admin_client, dataset_a_json):
    dataset_a_json["actors"][0]["person"] = {"name": "teppo", "email": "teppo@example.com"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201, res.data
    cached_item = dataset_cache.get(res.data["id"])
    assert cached_item.get("id") == res.data["id"]
    assert cached_item.get("title") == dataset_a_json["title"]
    assert cached_item.get("actors") == [
        {
            "id": matchers.Any(),
            "person": {
                "id": matchers.Any(),
                "name": "teppo",
                "email": matchers.Any(),
            },
            "organization": {"id": matchers.Any(), "pref_label": {"en": "test org"}},
            "roles": ["creator", "publisher"],
        }
    ]

    # Check that emails are stored in cache as PrivateEmailValue objects
    cached_email = cached_item["actors"][0]["person"]["email"]
    assert isinstance(cached_email, PrivateEmailValue)
    assert cached_email.value == "teppo@example.com"
    assert cached_item.get("temporal") == dataset_a_json["temporal"]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset_in_cache_overwrite_old(dataset_cache, admin_client, dataset_a_json):
    dataset_a_json["title"] = {"en": "old title"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    update_json = {"title": {"en": "new title"}}
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}", update_json, content_type="application/json"
    )
    assert res.status_code == 200

    cached_item = dataset_cache.get(dataset_id)
    assert cached_item["title"] == {"en": "new title"}


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_get_cached_dataset(dataset_cache, admin_client, dataset_a_json):
    """Verify that dataset uses cached data."""
    dataset_a_json["title"] = {"en": "original title"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    # Modify data stored in cache without altering modification timestamp
    cached_item = {**dataset_cache.get(dataset_id)}
    cached_item["title"] = {"en": "title modified in cache"}
    dataset_cache.set(dataset_id, cached_item)

    # Dataset should use altered data from cache
    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert res.status_code == 200
    assert res.data["title"] == {"en": "title modified in cache"}

    # Alter timestamp in cache
    cached_item["_modified"] += timedelta(seconds=1.234)
    dataset_cache.set(dataset_id, cached_item)

    # Timestamp in cache no longer matches dataset, cache value should be ignored
    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert res.status_code == 200
    assert res.data["title"] == {"en": "original title"}


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_get_dataset_in_cache_modified(dataset_cache, admin_client, dataset_a_json):
    """Test that requesting dataset updates the cache entry if needed."""
    now = timezone.now()
    dataset_a_json["title"] = {"en": "original title"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["title"] == {"en": "original title"}
    dataset_id = res.data["id"]
    assert dataset_cache.get(dataset_id)["title"] == {"en": "original title"}

    # Get should overwrite cache entry that is newer than the dataset. This solves
    # some potential edge cases compared to not overwriting newer cache data.
    #
    # The main cases where cache can contain newer data are:
    # - Updated dataset is written to cache while another request is reading datasets
    #   - Overwrite: Cache gets old data. Next query will need to update cache entry again.
    #   - Don't overwrite: Cache contains latest data.
    # - Dataset transaction fails after the updated version is already in the cache
    #   - Overwrite: Cache contains latest committed data.
    #   - Don't overwrite: Cache will contain stale data until dataset is modified.
    future_cached_item = dataset_cache.get(dataset_id)
    future_cached_item["title"] = {"en": "future title"}
    future_cached_item["_modified"] = now + timedelta(weeks=10)
    dataset_cache.set(dataset_id, future_cached_item)

    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert res.status_code == 200
    assert res.data["title"] == {"en": "original title"}
    assert dataset_cache.get(dataset_id)["title"] == {"en": "original title"}

    # Get should overwrite cache entry that is older than the dataset.
    old_cached_item = dataset_cache.get(dataset_id)
    old_cached_item["title"] = {"en": "old title"}
    old_cached_item["_modified"] = now - timedelta(weeks=10)
    dataset_cache.set(dataset_id, old_cached_item)

    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert res.status_code == 200
    assert res.data["title"] == {"en": "original title"}
    assert dataset_cache.get(dataset_id)["title"] == {"en": "original title"}


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_cache_update_files_on_draft_merge(dataset_cache, admin_client, dataset_a_json, file_tree):
    """When files are added in draft merge, the cached dataset should have the new files."""
    dataset_a_json["title"] = {"en": "Old title"}
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201, res.data

    # Create draft and add files
    dataset_id = res.data["id"]
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/create-draft", content_type="application/json"
    )
    assert res.status_code == 201, res.data

    draft_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{draft_id}",
        {
            "title": {"en": "Updated title"},
            "fileset": {
                "storage_service": file_tree["storage"].storage_service,
                "csc_project": file_tree["storage"].csc_project,
                "directory_actions": [{"pathname": "/"}],
            },
        },
        content_type="application/json",
    )
    assert res.status_code == 200, res.data

    # Cache for the published dataset should still show the original values
    cached_item = dataset_cache.get(dataset_id)
    assert cached_item["title"] == {"en": "Old title"}
    assert cached_item.get("fileset") is None

    # Draft is merged, cache for the dataset should have new values
    res = admin_client.post(f"/v3/datasets/{draft_id}/publish", content_type="application/json")
    assert res.status_code == 200, res.data

    cached_item = dataset_cache.get(dataset_id)
    assert cached_item["title"] == {"en": "Updated title"}
    assert cached_item["fileset"]["total_files_count"] == 8
