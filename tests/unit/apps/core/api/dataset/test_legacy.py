import pytest
from rest_framework.reverse import reverse

from apps.core.models import LegacyDataset
from apps.actors.factories import OrganizationFactory
from apps.core.models.catalog_record.dataset import Dataset

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.dataset, pytest.mark.legacy]


def test_create_legacy_dataset(legacy_dataset_a):
    assert legacy_dataset_a.status_code == 201


def test_create_same_legacy_dataset_twice(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    assert legacy_dataset_a.status_code == 201
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert LegacyDataset.available_objects.count() == 1


def test_edit_legacy_dataset(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["language"].append(
        {
            "identifier": "http://lexvo.org/id/iso639-3/est",
            "title": {"en": "Estonian", "fi": "Viron kieli", "und": "viro"},
        }
    )
    res = admin_client.put(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        ),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200


def test_get_organization_with_duplicate_get(legacy_dataset_a):
    assert legacy_dataset_a.status_code == 201
    dataset = LegacyDataset.objects.first()
    org1 = OrganizationFactory.create(pref_label={"en": "University of Helsinki"}, url=None)
    org2 = OrganizationFactory.create(
        pref_label={"en": "University of Helsinki", "fi": "Helsingin Yliopisto"}, url=None
    )
    org3 = dataset.get_or_create_v3_org_from_v2_org(
        {
            "@type": "Organization",
            "name": {
                "en": "University of Helsinki",
            },
        }
    )
    best = dataset.choose_between_orgs(org1, org3)
    assert str(org2.id) == str(org3.id)
    assert str(best.id) == str(org2.id)


def test_edit_legacy_dataset_deprecation(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    # deprecation boolean should be converted into timestamp
    legacy_dataset_a_json["dataset_json"]["deprecated"] = True
    res = admin_client.put(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        ),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    dataset_id = res.data["id"]
    dataset = Dataset.objects.get(id=dataset_id)
    assert dataset.deprecated is not None
    dataset_deprecation_date = dataset.deprecated

    # deprecation timestamp should not change for already deprecated legacy dataset
    legacy_dataset_a_json["dataset_json"]["research_dataset"][
        "modified"
    ] = "2023-12-24 18:00:00+00:00"
    res = admin_client.put(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        ),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    dataset = Dataset.objects.get(id=dataset_id)
    assert dataset.deprecated == dataset_deprecation_date


def test_delete_legacy_dataset(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    res = admin_client.delete(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        )
    )
    assert res.status_code == 204
    assert LegacyDataset.available_objects.count() == 0
