import logging
import uuid
from unittest.mock import ANY

import pytest
from django.contrib.auth.models import Group
from django.db import connections, transaction, utils
from psycopg.errors import LockNotAvailable
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers
from watson.models import SearchEntry

from apps.core import factories
from apps.core.factories import DatasetFactory, MetadataProviderFactory
from apps.core.models import OtherIdentifier
from apps.core.models.catalog_record.dataset import Dataset
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_create_dataset(admin_client, dataset_a_json, dataset_signal_handlers):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict({"user": "admin", "organization": "admin"}, res.data["metadata_owner"])
    assert_nested_subdict(dataset_a_json, res.data, ignore=["generate_pid_on_publish"])
    assert res.data["metadata_repository"] == "Fairdata"  # Constant value
    dataset_signal_handlers.assert_call_counts(created=1, updated=0)


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_update_dataset(admin_client, dataset_a_json, dataset_b_json, dataset_signal_handlers):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_signal_handlers.assert_call_counts(created=1, updated=0)
    dataset_signal_handlers.reset()
    id = res.data["id"]
    dataset_b_json["persistent_identifier"] = res.data["persistent_identifier"]
    res = admin_client.put(f"/v3/datasets/{id}", dataset_b_json, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(dataset_b_json, res.data, ignore=["generate_pid_on_publish"])
    dataset_signal_handlers.assert_call_counts(created=0, updated=1)


def test_update_dataset_with_project(
    admin_client, dataset_a_json, dataset_d_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = admin_client.patch(f"/v3/datasets/{id}", dataset_d_json, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(dataset_d_json, res.data)


def test_create_dataset_invalid_catalog(admin_client, dataset_a_json):
    dataset_a_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-does-not-exist"
    response = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "value,expected_error",
    [
        ([{"url": "non_existent"}], "Language entries not found for given URLs: non_existent"),
        ([{"foo": "bar"}], "'url' field must be defined for each object in the list"),
        (["FI"], "Each item in the list must be an object with the field 'url'"),
        ("FI", 'Expected a list of items but got type "str".'),
    ],
)
def test_create_dataset_invalid_language(admin_client, dataset_a_json, value, expected_error):
    """
    Try creating a dataset with an improperly formatted 'language' field.
    Each error case has a corresponding error message.
    """
    dataset_a_json["language"] = value

    response = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["language"] == [expected_error]


def test_delete_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data, ignore=["generate_pid_on_publish"])
    res = admin_client.delete(f"/v3/datasets/{id}")
    assert res.status_code == 204


def test_get_removed_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    # create a dataset and check it works
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    id = res1.data["id"]
    res2 = admin_client.get(f"/v3/datasets/{id}")
    assert res2.status_code == 200
    assert_nested_subdict(dataset_a_json, res2.data, ignore=["generate_pid_on_publish"])

    # delete the dataset...
    res3 = admin_client.delete(f"/v3/datasets/{id}")
    assert res3.status_code == 204

    # ...and check that it
    # 1. cannot be found without query parameter
    res4 = admin_client.get(f"/v3/datasets/{id}")
    assert res4.status_code == 404
    # 2. can be found with the query parameter
    res5 = admin_client.get(f"/v3/datasets/{id}?include_removed=True")
    assert res5.status_code == 200
    assert_nested_subdict(dataset_a_json, res5.data, ignore=["generate_pid_on_publish"])


def test_list_datasets_with_default_pagination(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"))
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [ANY, ANY],
    }


def test_list_datasets_fields_param(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"), {"fields": "id,created"})
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [{"id": ANY, "created": ANY}, {"id": ANY, "created": ANY}],
    }


def test_list_datasets_faulty_fields_param(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"), {"fields": "id,foo,bar,created"})
    assert res.status_code == 400
    assert res.data == {"fields": "Fields not found in dataset: foo,bar"}


def test_list_datasets_with_invalid_query_param(admin_client, dataset_a):
    res = admin_client.get(reverse("dataset-list"), {"päginätiön": "false", "offzet": 10})
    assert res.status_code == 400
    assert res.json() == {
        "päginätiön": "Unknown query parameter",
        "offzet": "Unknown query parameter",
    }

    # unknown params should be ok in non-strict mode
    res = admin_client.get(
        reverse("dataset-list"), {"päginätiön": "false", "offzet": 10, "strict": "false"}
    )
    assert res.status_code == 200


def test_list_datasets_with_pagination(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"), {"pagination": "true"})
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [ANY, ANY],
    }


def test_list_datasets_with_no_pagination(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"), {"pagination": "false"})
    assert res.status_code == 200
    assert res.data == [ANY, ANY]


def test_create_dataset_with_metadata_owner(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json["metadata_owner"] = {
        "organization": "organization-a.fi",
        "user": "metax-user-a",
    }
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")

    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json["metadata_owner"], res.data["metadata_owner"])


def test_patch_metadata_owner(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    new_owner = {
        "organization": "organization-a.fi",
        "user": "metax-user-a",
    }
    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"metadata_owner": new_owner},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict(new_owner, res.data["metadata_owner"])


def test_put_dataset_by_user(
    user_client, dataset_a_json, data_catalog, reference_data, requests_mock
):
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    user = res.data["metadata_owner"]["user"]

    # metadata owner should remain unchanged by put
    dataset_a_json["persistent_identifier"] = res.data["persistent_identifier"]
    res = user_client.put(
        f"/v3/datasets/{res.data['id']}", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["metadata_owner"]["user"] == user


def test_patch_metadata_owner_not_allowed(
    user_client, dataset_a_json, data_catalog, reference_data
):
    """End-user cannot use custom metadata owner values."""
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    new_owner = {
        "organization": "organization-a.fi",
        "user": "metax-user-a",
    }
    dataset_id = res.data["id"]
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"metadata_owner": new_owner},
        content_type="application/json",
    )
    assert res.status_code == 400


def test_create_dataset_with_actor(dataset_c, data_catalog, reference_data):
    assert dataset_c.status_code == 201
    assert len(dataset_c.data["actors"]) == 2


def test_modify_dataset_actor_roles(
    admin_client, dataset_c, dataset_c_json, data_catalog, reference_data
):
    assert dataset_c.status_code == 201
    assert len(dataset_c.data["actors"]) == 2
    dataset_c_json["actors"][0]["roles"].append("publisher")
    res = admin_client.put(
        f"/v3/datasets/{dataset_c.data['id']}", dataset_c_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data["actors"]) == 2
    assert "publisher" in res.data["actors"][0]["roles"]
    assert "creator" in res.data["actors"][0]["roles"]


@pytest.mark.django_db
def test_create_dataset_with_other_identifiers(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json["other_identifiers"] = [
        {
            "identifier_type": {
                "url": "http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi"
            },
            "notation": "foo",
        },
        {"notation": "bar"},
        {"old_notation": "foo", "notation": "bar"},
    ]

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert len(res.data["other_identifiers"]) == 3


@pytest.mark.django_db
def test_update_dataset_with_other_identifiers(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    # Create a dataset with other_identifiers
    dataset_a_json["other_identifiers"] = [
        {
            "identifier_type": {
                "url": "http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi"
            },
            "notation": "foo",
        },
        {"notation": "bar"},
        {"old_notation": "foo", "notation": "baz"},
    ]

    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert len(res.data["other_identifiers"]) == 3
    assert_nested_subdict(dataset_a_json["other_identifiers"], res.data["other_identifiers"])

    ds_id = res.data["id"]

    # Update other_identifiers
    dataset_a_json["other_identifiers"] = [
        {
            "identifier_type": {
                "url": "http://uri.suomi.fi/codelist/fairdata/identifier_type/code/urn"
            },
            "notation": "foo",
        },
        {
            "identifier_type": {
                "url": "http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi"
            },
            "notation": "new_foo",
        },
        {"notation": "updated_bar"},
        {"old_notation": "updated_foo", "notation": "updated_baz"},
    ]
    res = admin_client.patch(
        f"/v3/datasets/{ds_id}", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data["other_identifiers"]) == 4
    assert_nested_subdict(dataset_a_json["other_identifiers"], res.data["other_identifiers"])

    # Assert that the old other_identifiers don't exist in the db anymore
    new_count = OtherIdentifier.available_objects.all().count()
    assert new_count == 4


def test_dataset_put_maximal_and_minimal(
    admin_client, dataset_maximal_json, reference_data, data_catalog
):
    res = admin_client.post(
        "/v3/datasets?include_nulls=true", dataset_maximal_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert_nested_subdict(dataset_maximal_json, res.json())

    minimal_json = {
        "data_catalog": dataset_maximal_json["data_catalog"],
        "title": dataset_maximal_json["title"],
        "generate_pid_on_publish": "URN",
    }
    res = admin_client.put(
        f"/v3/datasets/{res.data['id']}?include_nulls=true",
        minimal_json,
        content_type="application/json",
    )
    assert res.status_code == 200

    # writable fields not in minimal_json should be cleared to falsy values
    assert list(sorted(key for key, value in res.data.items() if value)) == [
        "api_version",
        "created",
        "data_catalog",
        "dataset_versions",
        "draft_revision",
        "generate_pid_on_publish",
        "id",
        "metadata_owner",
        "metadata_repository",
        "modified",
        "state",
        "title",
        "version",
    ]


def test_dataset_patch_maximal_and_minimal(
    admin_client, dataset_maximal_json, reference_data, data_catalog
):
    res = admin_client.post("/v3/datasets", dataset_maximal_json, content_type="application/json")
    assert res.status_code == 201
    maximal_data = res.json()

    minimal_json = {
        "description": {"en": "new description"},
    }
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}", minimal_json, content_type="application/json"
    )
    assert res.status_code == 200
    minimal_data = res.json()

    # fields in minimal_json should replace values in maximal, others unchanged
    assert minimal_data == {
        **maximal_data,
        **minimal_json,
        "modified": matchers.DateTimeStr(),  # match any datetime
        "draft_revision": 2,  # increased by 1 on save
    }


def test_dataset_put_remove_fileset(
    admin_client, dataset_maximal_json, reference_data, data_catalog
):
    dataset_maximal_json.pop("remote_resources")
    FileStorageFactory(storage_service="ida", csc_project="project")
    dataset_maximal_json["fileset"] = {
        "storage_service": "ida",
        "csc_project": "project",
    }
    res = admin_client.post("/v3/datasets", dataset_maximal_json, content_type="application/json")
    assert res.status_code == 201

    # PUT without fileset would remove existing fileset which is not allowed
    minimal_json = {
        "data_catalog": dataset_maximal_json["data_catalog"],
        "title": dataset_maximal_json["title"],
    }
    res = admin_client.put(
        f"/v3/datasets/{res.data['id']}", minimal_json, content_type="application/json"
    )
    assert res.status_code == 400
    assert "not allowed" in res.json()["fileset"]


def test_dataset_restricted(admin_client, dataset_a_json, reference_data, data_catalog):
    dataset_a_json["access_rights"]["access_type"] = {
        "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"
    }
    dataset_a_json["access_rights"]["restriction_grounds"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"}
    ]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.json(), ignore=["generate_pid_on_publish"])


def test_create_dataset_require_data_catalog(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json["state"] = "published"
    dataset_a_json.pop("data_catalog")
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Dataset has to have a data catalog when publishing" in str(res.data["data_catalog"])


def test_create_dataset_draft_without_catalog(
    user_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json.pop("data_catalog")
    dataset_a_json["state"] = "draft"
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)

    # make sure the dataset can also be updated
    res = user_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"title": {"en": "test"}},
        content_type="application/json",
    )
    assert res.status_code == 200


def test_flush_dataset_by_service(service_client, dataset_a_json, data_catalog, reference_data):
    """Flush should delete dataset from database."""
    res = service_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]

    # Not external, not catalog admin
    res = service_client.delete(f"/v3/datasets/{dataset_id}?flush=true")
    assert res.status_code == 403

    # external, not catalog admin
    data_catalog.is_external = True
    data_catalog.save()
    res = service_client.delete(f"/v3/datasets/{dataset_id}?flush=true")
    assert res.status_code == 403

    # Not external, catalog admin
    data_catalog.is_external = False
    data_catalog.save()
    data_catalog.dataset_groups_admin.add(Group.objects.get(name="test"))
    res = service_client.delete(f"/v3/datasets/{dataset_id}?flush=true")
    assert res.status_code == 403

    # Both external and catalog admin -> ok
    data_catalog.is_external = True
    data_catalog.save()
    res = service_client.delete(f"/v3/datasets/{dataset_id}?flush=true")
    assert res.status_code == 204
    assert not Dataset.all_objects.filter(id=dataset_id).exists()


def test_flush_dataset_by_user(user_client, dataset_a_json, data_catalog, reference_data):
    """Flush should not be allowed for regular user."""
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = user_client.delete(f"/v3/datasets/{id}?flush=true")
    assert res.status_code == 403
    assert Dataset.available_objects.filter(id=id).exists()

    # Delete without flush should only soft delete
    res = user_client.delete(f"/v3/datasets/{id}")
    assert res.status_code == 204
    assert Dataset.all_objects.filter(id=id).exists()
    assert not Dataset.available_objects.filter(id=id).exists()


def test_flush_draft(user_client, dataset_a_json, data_catalog, reference_data):
    """Flush should be allowed for drafts."""
    dataset_a_json["state"] = "draft"
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = user_client.delete(f"/v3/datasets/{id}?flush=true")
    assert res.status_code == 204
    assert not Dataset.available_objects.filter(id=id).exists()


def test_empty_description(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["state"] = "draft"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}?include_nulls=true",
        {"description": {"fi": "", "en": None}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["description"] == None


def test_api_version(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]
    assert res.data["api_version"] == 3
    Dataset.objects.filter(id=dataset_id).update(api_version=2)
    res = admin_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 200
    assert res.data["api_version"] == 3


def test_dataset_last_modified_by(admin_client, user_client, user):
    dataset = DatasetFactory(metadata_owner=MetadataProviderFactory(user=user))

    admin_client.patch(f"/v3/datasets/{dataset.id}", {}, content_type="application/json")
    dataset.refresh_from_db()
    assert dataset.last_modified_by.username == "admin"

    user_client.patch(f"/v3/datasets/{dataset.id}", {}, content_type="application/json")
    dataset.refresh_from_db()
    assert dataset.last_modified_by == user


def test_dataset_expanded_catalog(admin_client, dataset_a_json, data_catalog, reference_data):
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201

    res2 = admin_client.get(f"/v3/datasets/{res1.data['id']}")
    assert res2.status_code == 200
    assert isinstance(res2.data["data_catalog"], str)

    res3 = admin_client.get(f"/v3/datasets/{res1.data['id']}?expand_catalog=true")
    assert res3.status_code == 200
    assert isinstance(res3.data["data_catalog"], dict)


def test_many_actors(admin_client, dataset_a_json, data_catalog, reference_data):
    org = {"organization": {"pref_label": {"en": "organization"}}}
    dataset_a_json["actors"] = [
        {"person": {"name": f"Test person {i}"}, **org, "roles": ["creator"]} for i in range(100)
    ]
    dataset_a_json["actors"][0]["roles"].append("publisher")
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


def test_dataset_search_entry(admin_client, dataset_a_json, data_catalog, reference_data):
    """Check that search entry contains correct values from dataset."""
    dataset_a_json["other_identifiers"] = [{"notation": "doi:10.1337/other_identifier"}]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    entry = SearchEntry.objects.get(object_id=dataset_id)
    assert res.data["persistent_identifier"] in entry.title  # pid
    assert "Test dataset" in entry.title  # title
    assert "test subjects (persons)" in entry.title  # theme
    assert "Test dataset desc" in entry.description  # description
    assert "keyword another_keyword" in entry.description  # keywords
    assert "doi:10.1337/other_identifier" in entry.content  # entity.notation


def test_create_dataset_with_extra_fields(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json["test-abcd"] = "non valid field"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert str(res.data["test-abcd"][0]) == "Unexpected field"
    # with strict=false the dataset creation should get through
    res = admin_client.post(
        "/v3/datasets?strict=false", dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201


def test_dataset_citation(admin_client):
    minimal_json = {"title": {"en": "hello world"}, "bibliographic_citation": "   some text here "}
    res = admin_client.post("/v3/datasets", minimal_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data == matchers.DictContaining(
        {"title": {"en": "hello world"}, "bibliographic_citation": "some text here"}
    )


def test_get_dataset_include_nulls(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]
    res = admin_client.get(f"/v3/datasets/{dataset_id}", content_type="application/json")
    assert "deprecated" not in res.data
    res = admin_client.get(
        f"/v3/datasets/{dataset_id}?include_nulls=true", content_type="application/json"
    )
    assert res.data["deprecated"] == None


def test_missing_required_fields(
    admin_client, data_catalog, data_catalog_harvested, reference_data
):
    # title
    dataset = {"state": "published"}
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert "This field is required." in str(res.data["title"])

    dataset = {
        **dataset,
        "title": {"en": "test"},
        "actors": [{"roles": [], "organization": {"pref_label": {"en": "Test Org"}}}],
    }
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")

    data = res.json()
    assert res.status_code == 400
    assert "Dataset has to have a data catalog when publishing." in data["data_catalog"]
    assert "Dataset has to have access rights when publishing." in data["access_rights"]
    assert "Dataset has to have a description when publishing." in data["description"]
    assert "An actor with creator role is required." in data["actors"]
    assert "Exactly one actor with publisher role is required." in data["actors"]
    assert "All actors in a published dataset should have at least one role." in data["actors"]

    # data_catalog(ida), access_rights, description, actors
    dataset = {
        **dataset,
        "data_catalog": "urn:nbn:fi:att:data-catalog-ida",
        "access_rights": {
            "access_type": {"url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"},
        },
        "description": {"en": "test"},
        "actors": [
            {
                "roles": ["creator", "publisher"],
            }
        ],
    }

    # actors[].organization
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert (
        str(res.data["actors"][0]["organization"])
        == str(res.data["actors"][0]["organization"])
        == "This field is required"
    )

    dataset = {
        **dataset,
        "actors": [
            {
                "roles": ["creator", "publisher"],
                "organization": {"pref_label": {"en": "test org"}},
            }
        ],
    }

    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert "Dataset has to have a license when publishing." in str(res.data["access_rights"])

    # access_rights.license
    dataset["access_rights"]["license"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"}
    ]

    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 400
    assert "required by the catalog when publishing" in str(res.data["generate_pid_on_publish"])

    # data_catalog(harvested), access_rights, description, actors, license
    harvested_dataset = {**dataset, "data_catalog": "urn:nbn:fi:att:data-catalog-harvested"}
    harvested_res = admin_client.post(
        "/v3/datasets", harvested_dataset, content_type="application/json"
    )

    assert harvested_res.status_code == 400
    assert "Dataset has to have a persistent identifier" in str(
        harvested_res.data["persistent_identifier"]
    )

    # harvested_catalog: persistent_identifier
    harvested_dataset = {**harvested_dataset, "persistent_identifier": "PID"}
    harvested_res = admin_client.post(
        "/v3/datasets", harvested_dataset, content_type="application/json"
    )
    assert harvested_res.status_code == 201

    # continue with ida-dataset
    # ida-catalog: pid_type
    dataset = {**dataset, "generate_pid_on_publish": "URN"}
    res = admin_client.post("/v3/datasets", dataset, content_type="application/json")
    assert res.status_code == 201


def test_missing_restriction_grounds(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["access_rights"]["access_type"] = {
        "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted"
    }
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert (
        "Dataset access rights has to contain restriction grounds if access type is not 'Open'."
        in str(res.data["access_rights"])
    )

    dataset_a_json["access_rights"]["restriction_grounds"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"}
    ]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


def test_unnecessary_restriction_grounds(
    admin_client, dataset_a_json, data_catalog, reference_data
):
    dataset_a_json["access_rights"]["restriction_grounds"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"}
    ]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400
    assert "Open datasets do not accept restriction grounds." in str(res.data["access_rights"])

    dataset_a_json["access_rights"].pop("restriction_grounds")
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


def test_get_dataset_no_multiple_objects_error(service_client):
    """Check that multiple groups in dataset_groups_admin don't produce MultipleObjectsReturned error in query."""
    data_catalog = factories.DataCatalogFactory()
    data_catalog.dataset_groups_admin.add(Group.objects.get(name="test"))
    data_catalog.dataset_groups_admin.add(Group.objects.create(name="somegroup"))
    dataset = factories.PublishedDatasetFactory(data_catalog=data_catalog)
    res = service_client.patch(f"/v3/datasets/{dataset.id}", {}, content_type="application/json")
    assert res.status_code == 200


def test_not_a_list(admin_client, dataset_a_json, data_catalog, reference_data, monkeypatch):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    provenances = {
        "spatial": {
            "geographic_name": "Tapiola",
            "reference": {"url": "http://www.yso.fi/onto/yso/p105747"},
        },
    }

    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"provenance": provenances},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Expected a list" in res.json()["provenance"]["non_field_errors"][0]


def test_remove_rights(admin_client, dataset_a_json, data_catalog, reference_data):
    dataset = factories.DatasetFactory()
    dataset_id = dataset.id
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"access_rights": None},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert "access_rights" not in res.data


def test_omit_owner_user_when_no_edit_access(
    user_client, user_client_2, dataset_a_json, data_catalog, reference_data
):
    """Dataset metadata_owner.user should be hidden when user does not have edit access."""
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    _id = res.data["id"]

    res = user_client.get(f"/v3/datasets/{_id}", content_type="application/json")
    assert res.data["metadata_owner"]["user"] == "test_user"

    # Request dataset as another user
    res = user_client_2.get(f"/v3/datasets/{_id}", content_type="application/json")
    assert "user" not in res.data["metadata_owner"]


@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
def test_dataset_lock_for_update(admin_client):
    """Dataset update should lock the row for updating."""
    dataset = factories.PublishedDatasetFactory()
    with transaction.atomic():
        # Getting lock should fail because the update has locked the dataset
        with pytest.raises(utils.OperationalError) as ec:
            res = admin_client.patch(
                f"/v3/datasets/{dataset.id}", {}, content_type="application/json"
            )
            assert res.status_code == 200
            with transaction.atomic(using="extra_connection"):
                Dataset.objects.using("extra_connection").select_for_update(nowait=True).get(
                    id=dataset.id
                )
        assert isinstance(ec.value.__cause__, LockNotAvailable)

    with transaction.atomic(using="extra_connection"):
        # Transaction done, lock should be available now
        Dataset.objects.using("extra_connection").select_for_update(nowait=True).get(id=dataset.id)


@pytest.mark.django_db(databases=("default", "extra_connection"), transaction=True)
def test_dataset_lock_for_update_outside_transaction():
    """Dataset.lock_for_update should not do anything when not in transaction."""
    Dataset.lock_for_update(uuid.uuid4()) # Would throw error if select_for_update was called
