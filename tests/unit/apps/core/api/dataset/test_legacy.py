import pytest
from rest_framework.reverse import reverse

from apps.actors.factories import OrganizationFactory
from apps.core.models import LegacyDataset
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


def test_legacy_dataset_actors(admin_client, data_catalog, reference_data, legacy_dataset_a_json):
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    res = admin_client.get(
        reverse("dataset-detail", kwargs={"pk": res.data["id"]}), content_type="application/json"
    )
    data = res.json()

    # Check that actors are merged
    assert len(data["actors"]) == 3
    assert data["actors"][0]["person"]["name"] == "Toni Nurmi"
    assert sorted(data["actors"][0]["roles"]) == [
        "contributor",
        "creator",
        "publisher",
        "rights_holder",
    ]
    assert data["actors"][1]["person"]["name"] == "Teppo Testaaja"
    assert data["actors"][1]["organization"]["homepage"] == {
        "url": "https://example.com",
        "title": {"en": "Test homepage"},
    }
    assert data["actors"][1]["roles"] == ["creator"]
    assert data["actors"][2]["person"]["name"] == "Curator Person"
    assert data["actors"][2]["roles"] == ["curator"]

    actor_without_roles = {**res.json()["actors"][0]}
    actor_without_roles.pop("roles")
    assert actor_without_roles == res.json()["provenance"][0]["is_associated_with"][0]

    # Check that deprecated reference organization has been created
    res = admin_client.get(
        reverse("organization-list"),
        {
            "url": "http://uri.suomi.fi/codelist/fairdata/organization/code/legacyorg",
            "deprecated": True,
            "expand_children": True,
            "pagination": False,
        },
    )
    data = res.json()
    assert len(data) == 1
    assert data[0]["pref_label"]["en"] == "Reference organization from V2 not in V3"
    assert data[0]["deprecated"] is not None
    assert len(data[0]["children"]) == 1
    assert (
        data[0]["children"][0]["pref_label"]["en"]
        == "Reference organization department from V2 not in V3"
    )
    assert data[0]["children"][0]["deprecated"] is not None


def test_legacy_dataset_actors_invalid_refdata_parent(
    admin_client, data_catalog, reference_data, legacy_dataset_a_json
):
    """Reference organization cannot be child of non-reference organization."""
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["creator"] = {
        "name": "Toni Nurmi",
        "@type": "Person",
        "member_of": {
            "name": {"en": "Legacy reference org"},
            "@type": "Organization",
            "identifier": "http://uri.suomi.fi/codelist/fairdata/organization/code/somelegacyorg",
            "is_part_of": {
                "name": {"en": "this is not a reference org"},
                "@type": "Organization",
                "identifier": "http://example.com/thisisnotreferencedata",
            },
        },
    }
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert (
        "cannot be child of non-reference organization" in res.json()[0]["organization"]["parent"]
    )
