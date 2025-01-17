import copy
from datetime import datetime
from uuid import UUID

import pytest
from rest_framework.reverse import reverse
from tests.utils import matchers

from apps.core import factories
from apps.core.models import LegacyDataset
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.data_catalog import DataCatalog

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.dataset, pytest.mark.adapter]


def test_create_legacy_dataset(legacy_dataset_a):
    assert legacy_dataset_a.status_code == 201, legacy_dataset_a.data
    assert not legacy_dataset_a.data.get("migration_errors")
    assert legacy_dataset_a.data.get("preservation") is None


def test_create_same_legacy_dataset_twice(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    assert legacy_dataset_a.status_code == 201
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert not res.data.get("migration_errors")
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
    assert not res.data.get("migration_errors")


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
    assert not res.data.get("migration_errors")
    dataset_id = res.data["id"]
    dataset = Dataset.objects.get(id=dataset_id)
    assert isinstance(dataset.deprecated, datetime)


def test_delete_legacy_dataset(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    """Published legacy dataset should be soft deleted."""
    res = admin_client.delete(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        )
    )
    assert res.status_code == 204
    assert LegacyDataset.all_objects.count() == 1
    assert Dataset.all_objects.count() == 1
    assert LegacyDataset.available_objects.count() == 0
    assert Dataset.available_objects.count() == 0


def test_delete_legacy_dataset_draft(admin_client, legacy_dataset_a_json, reference_data):
    """Draft legacy dataset should be hard deleted."""
    legacy_dataset_a_json["dataset_json"]["state"] = "draft"
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    res = admin_client.delete(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        )
    )
    assert res.status_code == 204
    assert LegacyDataset.all_objects.count() == 0
    assert Dataset.all_objects.count() == 0
    assert LegacyDataset.available_objects.count() == 0
    assert Dataset.available_objects.count() == 0


def test_legacy_draft_use_doi_on_publish(admin_client, legacy_dataset_a_json, reference_data):
    legacy_dataset_a_json["dataset_json"]["state"] = "draft"
    legacy_dataset_a_json["dataset_json"]["research_dataset"][
        "preferred_identifier"
    ] = "draft:temp-pid"
    legacy_dataset_a_json["dataset_json"]["use_doi_for_published"] = True
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.generate_pid_on_publish == "DOI"


def test_legacy_draft_no_doi(admin_client, legacy_dataset_a_json, reference_data):
    legacy_dataset_a_json["dataset_json"]["state"] = "draft"
    legacy_dataset_a_json["dataset_json"]["research_dataset"][
        "preferred_identifier"
    ] = "draft:temp-pid"
    legacy_dataset_a_json["dataset_json"]["use_doi_for_published"] = False
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.generate_pid_on_publish == "URN"


def test_legacy_dataset_actors(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json
):
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
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
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json
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
    assert "cannot be child of non-reference organization" in res.json()["is_part_of"]


def test_legacy_dataset_relation(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json
):
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
    res = admin_client.get(
        reverse("dataset-detail", kwargs={"pk": res.data["id"]}), content_type="application/json"
    )
    data = res.json()
    assert len(data["relation"]) == 1
    assert data["relation"][0]["entity"]["entity_identifier"] == "external:dataset:identifier"
    assert (
        data["relation"][0]["entity"]["type"]["url"]
        == "http://uri.suomi.fi/codelist/fairdata/resource_type/code/physical_object"
    )


def test_edit_legacy_dataset_wrong_api_version(
    admin_client, legacy_dataset_a, legacy_dataset_a_json
):
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["language"].append(
        {
            "identifier": "http://lexvo.org/id/iso639-3/est",
            "title": {"en": "Estonian", "fi": "Viron kieli", "und": "viro"},
        }
    )
    identifier = legacy_dataset_a_json["dataset_json"]["identifier"]
    admin_client.patch(
        reverse("dataset-detail", kwargs={"pk": identifier}),
        {},
        content_type="application/json",
    )  # Should update api_version to 3
    res = admin_client.put(
        reverse("migrated-dataset-detail", args=[identifier]),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 400
    assert res.json() == {"detail": "Dataset has been modified with a later API version."}


def test_legacy_dataset_email(admin_client, legacy_dataset_a, legacy_dataset_a_json):
    legacy_dataset_a_json["dataset_json"]["access_granter"] = {
        "userid": "access-granter-user",
        "name": "Access Granter",
        "email": "accessgranter@example.com",
    }
    legacy_dataset_a_json["dataset_json"]["research_dataset"]["creator"][0][
        "email"
    ] = "hello@world.com"
    res = admin_client.put(
        reverse(
            "migrated-dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]
        ),
        legacy_dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 200
    assert not res.data.get("migration_errors")
    assert res.data["dataset_json"]["research_dataset"]["creator"][0]["email"] == "<hidden>"
    assert res.data["dataset_json"]["access_granter"] == "<hidden>"


def test_legacy_dataset_catalog(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json
):
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
    res = admin_client.get(
        reverse("dataset-detail", args=[legacy_dataset_a_json["dataset_json"]["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data.get("data_catalog") == "urn:nbn:fi:att:data-catalog-att"


def test_legacy_dataset_catalog_dft(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json
):
    dataset_json = legacy_dataset_a_json["dataset_json"]
    dataset_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-dft"
    dataset_json["research_dataset"]["preferred_identifier"] = "draft:some_pid"
    dataset_json["research_dataset"]["remote_resources"] = None
    dataset_json["state"] = "draft"
    dataset_json["draft_of"] = None
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert not res.data.get("migration_errors")

    res = admin_client.get(
        reverse("dataset-detail", args=[dataset_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200

    # Catalog urn:nbn:fi:att:data-catalog-dft should be removed along with the temporary PID
    assert res.data.get("data_catalog") is None
    assert res.data.get("persistent_identifier") is None
    assert res.data.get("state") == "draft"
    assert not DataCatalog.objects.filter(id="urn:nbn:fi:att:data-catalog-dft").exists()


@pytest.mark.parametrize(
    "persistent_identifier,pid_generated_by_fairdata,generate_pid_on_publish",
    [
        ("urn:nbn:fi:csc-jotain", True, "URN"),
        ("urn:nbn:fi:att:jotain-cscn", True, "URN"),
        ("urn:nbn:fi:eicsc", False, None),
        ("doi:10.23729/on-csc", True, "DOI"),
        ("doi:10.12345/eioo-csc", False, None),
        ("jokumuu:ei-csc", False, None),
    ],
)
def test_legacy_dataset_pid_attributes(
    admin_client,
    data_catalog,
    reference_data,
    legacy_dataset_a_json,
    persistent_identifier,
    pid_generated_by_fairdata,
    generate_pid_on_publish,
):
    dataset_json = legacy_dataset_a_json["dataset_json"]
    dataset_json["data_catalog"] = data_catalog.id
    dataset_json["research_dataset"]["preferred_identifier"] = persistent_identifier
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert not res.data.get("migration_errors")
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.persistent_identifier == persistent_identifier
    assert dataset.pid_generated_by_fairdata == pid_generated_by_fairdata
    assert dataset.generate_pid_on_publish == generate_pid_on_publish


def test_legacy_dataset_preservation_fields(
    admin_client,
    data_catalog_att,
    reference_data,
    legacy_dataset_a_json,
):
    contract = factories.ContractFactory(legacy_id=123)

    dataset_json = legacy_dataset_a_json["dataset_json"]
    dataset_json["contract"] = {"id": contract.legacy_id}
    dataset_json["preservation_state"] = 20
    dataset_json["preservation_description"] = "oke"
    dataset_json["preservation_reason_description"] = "Plz preserve"
    dataset_json["preservation_identifier"] = "preservation_id:123:jee"

    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert not res.data.get("migration_errors")

    res = admin_client.get(
        reverse("dataset-detail", args=[dataset_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preservation"] == {
        "id": matchers.Any(),
        "contract": str(contract.id),
        "state": 20,
        "state_modified": matchers.DateTimeStr(),
        "description": {"und": "oke"},
        "reason_description": "Plz preserve",
        "preservation_identifier": "preservation_id:123:jee",
        "pas_package_created": False,
        "pas_process_running": False,
    }


def test_legacy_dataset_preservation_fields_contract_errors(
    admin_client,
    data_catalog_att,
    reference_data,
    legacy_dataset_a_json,
):
    contract = factories.ContractFactory(legacy_id=123)

    dataset_json = legacy_dataset_a_json["dataset_json"]
    dataset_json["contract"] = {"iidee": contract.legacy_id}
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json() == {"contract": "Missing contract.id"}

    dataset_json["contract"] = {"id": "not an integer"}
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json() == {"contract": "Invalid value"}

    dataset_json["contract"] = {"id": 1337}
    res = admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert res.json() == {"contract": "Contract with legacy_id=1337 not found"}


@pytest.mark.parametrize("origin_first", [True, False])
def test_legacy_dataset_preservation_dataset(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json, origin_first, contract
):
    """Test creating dataset and PAS copy."""
    legacy_dataset_a_json["dataset_json"]["contract"] = {"id": 1}
    origin_version = copy.deepcopy(legacy_dataset_a_json)
    origin_json = origin_version["dataset_json"]
    origin_json["identifier"] = str(UUID(int=1))
    origin_json["research_dataset"]["preferred_identifier"] = "pid:1"
    origin_json["preservation_dataset_version"] = {
        "identifier": str(UUID(int=2)),
        "preservation_state": 0,
    }
    origin_json["preservation_dataset_origin_version"] = None

    pas_version = copy.deepcopy(legacy_dataset_a_json)
    pas_json = pas_version["dataset_json"]
    pas_json["identifier"] = str(UUID(int=2))
    pas_json["research_dataset"]["preferred_identifier"] = "pid:2"
    pas_json["preservation_dataset_version"] = None
    pas_json["preservation_dataset_origin_version"] = {
        "identifier": str(UUID(int=1)),
        "preservation_state": -1,
    }

    # Order in which datasets are migrated should not matter
    if origin_first:
        payloads = [origin_version, pas_version]
    else:
        payloads = [pas_version, origin_version]

    for payload in payloads:
        res = admin_client.post(
            reverse("migrated-dataset-list"), payload, content_type="application/json"
        )
        assert res.status_code == 201, res.data
        assert not res.data.get("migration_errors")

    # Check origin version preservation links
    res = admin_client.get(
        reverse("dataset-detail", args=[origin_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preservation"].get("dataset_version") == {
        "id": pas_json["identifier"],
        "persistent_identifier": pas_json["research_dataset"]["preferred_identifier"],
        "preservation_state": 0,
    }
    assert data["preservation"].get("dataset_origin_version") is None

    # Check pas version preservation links
    res = admin_client.get(
        reverse("dataset-detail", args=[pas_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preservation"].get("dataset_version") is None
    assert data["preservation"].get("dataset_origin_version") == {
        "id": origin_json["identifier"],
        "persistent_identifier": origin_json["research_dataset"]["preferred_identifier"],
        "preservation_state": 0,
    }


def test_legacy_dataset_preservation_dataset_update(
    admin_client, data_catalog_att, reference_data, legacy_dataset_a_json, contract
):
    """Test updating existing legacy dataset to make preservation links."""
    # Original dataset is created without preservation info
    origin_version = copy.deepcopy(legacy_dataset_a_json)
    res = admin_client.post(
        reverse("migrated-dataset-list"), origin_version, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert not res.data.get("migration_errors")

    # PAS version is created with no preservation links yet because original has no preservation
    pas_version = copy.deepcopy(legacy_dataset_a_json)
    pas_json = pas_version["dataset_json"]
    pas_json["contract"] = {"id": 1}
    pas_json["identifier"] = str(UUID(int=2))
    pas_json["research_dataset"]["preferred_identifier"] = "pid:2"
    pas_json["preservation_dataset_version"] = None
    pas_json["preservation_dataset_origin_version"] = {"identifier": str(UUID(int=1))}
    res = admin_client.post(
        reverse("migrated-dataset-list"), pas_version, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert not res.data.get("migration_errors")

    # Original dataset is updated with preservation info, preservation links are created
    origin_json = origin_version["dataset_json"]
    origin_json["contract"] = {"id": 1}
    origin_json["identifier"] = str(UUID(int=1))
    origin_json["research_dataset"]["preferred_identifier"] = "pid:1"
    origin_json["preservation_dataset_version"] = {"identifier": str(UUID(int=2))}
    origin_json["preservation_dataset_origin_version"] = None
    res = admin_client.post(
        reverse("migrated-dataset-list"), origin_version, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert not res.data.get("migration_errors")

    # Check origin version preservation links
    res = admin_client.get(
        reverse("dataset-detail", args=[origin_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preservation"].get("dataset_version") == {
        "id": pas_json["identifier"],
        "persistent_identifier": pas_json["research_dataset"]["preferred_identifier"],
        "preservation_state": 0,
    }
    assert data["preservation"].get("dataset_origin_version") is None

    # Check PAS version preservation links
    res = admin_client.get(
        reverse("dataset-detail", args=[pas_json["identifier"]]),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preservation"].get("dataset_version") is None
    assert data["preservation"].get("dataset_origin_version") == {
        "id": origin_json["identifier"],
        "persistent_identifier": origin_json["research_dataset"]["preferred_identifier"],
        "preservation_state": 0,
    }
