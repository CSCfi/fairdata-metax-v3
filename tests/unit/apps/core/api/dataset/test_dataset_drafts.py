import json
import logging
from unittest.mock import ANY

import pytest
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers

from apps.core import factories
from apps.core.factories import DatasetFactory, MetadataProviderFactory
from apps.core.models import OtherIdentifier
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.concepts import IdentifierType
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def pop_nested_ids(dataset: dict) -> dict:
    """Remove ids from nested dicts, return id to dict mapping."""
    ids = {}

    def _pop(object):
        if isinstance(object, list):
            object = enumerate(object)
        if isinstance(object, dict):
            if "id" in object:
                obj_id = object.pop("id")
                if not "pref_label" in object:  # ignore refdata
                    ids[obj_id] = object
            for value in object.values():
                _pop(value)

    _pop(dataset)
    return ids


def test_create_draft(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/create-draft", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    draft = res.data

    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert res.status_code == 200
    original = res.data

    assert original["state"] == "published"
    assert draft["state"] == "draft"
    assert original["id"] in draft["draft_of"]
    assert draft["id"] in original["next_draft"]
    metadata_owner_id = draft["metadata_owner"]["id"]
    assert draft["metadata_owner"] == original["metadata_owner"]

    # Remove fields that should be different
    for field in [
        "id",
        "state",
        "next_draft",
        "draft_of",
        "next_version",
        "last_version",
        "previous_version",
        "first_version",
        "published_revision",
        "created",
        "modified",
        "persistent_identifier",
    ]:
        original.pop(field)
        draft.pop(field)

    # Nested data should be equal but with different ids (except refdata)
    original_ids = pop_nested_ids(original)
    draft_ids = pop_nested_ids(draft)
    assert original == draft

    # Check that no nested ids are shared
    original_ids.pop(metadata_owner_id)
    draft_ids.pop(metadata_owner_id)
    assert set(original_ids).intersection(draft_ids) == set()


def test_create_draft_from_draft(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/create-draft", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json()["state"] == "Dataset needs to be published before creating a new draft."


def test_create_draft_twice(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/create-draft", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    res = admin_client.post(
        f"/v3/datasets/{dataset_id}/create-draft", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json()["next_draft"] == "Dataset already has a draft."


def test_create_draft_by_changing_state(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}", {"state": "draft"}, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json()["state"] == "Value cannot be changed directly for an existing dataset."
