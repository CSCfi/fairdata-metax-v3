import pytest
from rest_framework.reverse import reverse

from apps.core.models import LegacyDataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.legacy]


def test_create_legacy_dataset(legacy_dataset_a):
    assert legacy_dataset_a.status_code == 201


def test_create_same_legacy_dataset_twice(client, legacy_dataset_a, legacy_dataset_a_json):
    assert legacy_dataset_a.status_code == 201
    res = client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert LegacyDataset.available_objects.count() == 1


def test_edit_legacy_dataset(client, legacy_dataset_a, legacy_dataset_a_json):
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["language"].append(
        {
            "identifier": "http://lexvo.org/id/iso639-3/est",
            "title": {"en": "Estonian", "fi": "Viron kieli", "und": "viro"},
        }
    )
    res = client.put(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        ),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200


def test_delete_legacy_dataset(client, legacy_dataset_a, legacy_dataset_a_json):
    res = client.delete(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        )
    )
    assert res.status_code == 204
    assert LegacyDataset.available_objects.count() == 0
