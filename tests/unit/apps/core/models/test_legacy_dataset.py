import uuid

import pytest

from apps.core.models import Dataset, LegacyDataset

pytestmark = [pytest.mark.django_db, pytest.mark.adapter]


def test_legacy_dataset_api_version():
    dataset_json_without_version = {
        "identifier": str(uuid.uuid4()),
        "research_dataset": {"title": {"en": "Hello"}},
        "metadata_provider_user": "test_user",
        "metadata_provider_org": "test_org",
        "cumulative_state": 0,
        "date_created": "2022-02-02T02:02:02Z",
        "state": "draft",
    }

    # By default, API version comes from dataset_json
    dataset_json = {
        "api_meta": {"version": 2},
        **dataset_json_without_version,
        "identifier": str(uuid.uuid4()),
    }
    d = LegacyDataset(dataset_json=dataset_json)
    d.save()
    d.update_from_legacy()
    assert d.dataset.api_version == 2

    # Default API version 1 if not in json
    d = LegacyDataset(dataset_json=dataset_json_without_version)
    d.save()
    d.update_from_legacy()
    assert d.dataset.api_version == 1
