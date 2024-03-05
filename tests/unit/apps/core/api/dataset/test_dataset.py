import json
import logging
from unittest.mock import ANY

import pytest
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers
from watson.models import SearchEntry

from apps.core import factories
from apps.core.factories import DatasetFactory, MetadataProviderFactory
from apps.core.models import OtherIdentifier
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.concepts import IdentifierType
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict({"user": "admin", "organization": "admin"}, res.data["metadata_owner"])
    assert_nested_subdict(dataset_a_json, res.data)


def test_update_dataset(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = admin_client.put(f"/v3/datasets/{id}", dataset_b_json, content_type="application/json")
    assert res.status_code == 200
    assert_nested_subdict(dataset_b_json, res.data)


def test_filter_pid(
    admin_client, dataset_a_json, dataset_b_json, datacatalog_harvested_json, reference_data
):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_b_json["data_catalog"] = datacatalog_harvested_json["id"]
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = admin_client.get("/v3/datasets?persistent_identifier=some_pid")
    assert res.data["count"] == 1


def test_search_pid(
    admin_client, dataset_a_json, dataset_b_json, datacatalog_harvested_json, reference_data
):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    dataset_a_json["data_catalog"] = datacatalog_harvested_json["id"]
    dataset_b_json["data_catalog"] = datacatalog_harvested_json["id"]
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = admin_client.get("/v3/datasets?search=some_pid")
    assert res.data["count"] == 1


def test_aggregation_and_filters(
    admin_client, dataset_a_json, dataset_b_json, dataset_c_json, data_catalog, reference_data
):
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_c_json, content_type="application/json")
    res = admin_client.get("/v3/datasets")
    assert res.data["count"] == 3
    assert res.data.get("aggregations") != None
    assert list(sorted(key for key, value in res.data["aggregations"].items())) == [
        "access_type",
        "creator",
        "data_catalog",
        "field_of_science",
        "file_type",
        "infrastructure",
        "keyword",
        "organization",
        "project",
    ]
    aggregations = res.data["aggregations"]

    for aggregation in aggregations.values():
        if len(aggregation["hits"]):
            value = (
                aggregation["hits"][0]["value"].get("fi")
                or aggregation["hits"][0]["value"].get("en")
                or aggregation["hits"][0]["value"].get("und")
            )
            count = aggregation["hits"][0]["count"]
            res = admin_client.get(f"/v3/datasets?{aggregation['query_parameter']}={value}")
            assert res.data["count"] == count


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
    assert_nested_subdict(dataset_a_json, res.data)
    res = admin_client.delete(f"/v3/datasets/{id}")
    assert res.status_code == 204


def test_get_removed_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    # create a dataset and check it works
    res1 = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res1.status_code == 201
    id = res1.data["id"]
    res2 = admin_client.get(f"/v3/datasets/{id}")
    assert res2.status_code == 200
    assert_nested_subdict(dataset_a_json, res2.data)

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
    assert_nested_subdict(dataset_a_json, res5.data)


def test_list_datasets_with_ordering(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_a_id = res.data["id"]
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    admin_client.put(
        f"/v3/datasets/{dataset_a_id}",
        dataset_a_json,
        content_type="application/json",
    )
    res = admin_client.get("/v3/datasets?ordering=created")
    assert_nested_subdict(
        {0: dataset_a_json, 1: dataset_b_json}, dict(enumerate((res.data["results"])))
    )

    res = admin_client.get("/v3/datasets?ordering=modified")
    assert_nested_subdict(
        {0: dataset_b_json, 1: dataset_a_json}, dict(enumerate((res.data["results"])))
    )


def test_list_datasets_with_default_pagination(admin_client, dataset_a, dataset_b):
    res = admin_client.get(reverse("dataset-list"))
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [ANY, ANY],
        "aggregations": ANY,
    }


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
        "aggregations": ANY,
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


def test_put_dataset_by_user(user_client, dataset_a_json, data_catalog, reference_data):
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    user = res.data["metadata_owner"]["user"]

    # metadata owner should remain unchanged by put
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


def test_owned_dataset(
    admin_client, user_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    """End-user cannot use custom metadata owner values."""
    dataset_a_json["state"] = "published"
    dataset_b_json["state"] = "published"
    dataset_b_json["actors"] = [
        {"roles": ["creator", "publisher"], "organization": {"pref_label": {"en": "org"}}}
    ]
    res = admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    assert res.status_code == 201
    res = user_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]
    assert res.status_code == 201

    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=false", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["count"] == 2

    res = user_client.get(
        "/v3/datasets?only_owned_or_shared=true", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["id"] == dataset_id


def test_create_dataset_with_actor(dataset_c, data_catalog, reference_data):
    assert dataset_c.status_code == 201
    assert len(dataset_c.data["actors"]) == 2


def test_edit_dataset_actor(admin_client, dataset_c, data_catalog, reference_data):
    assert dataset_c.status_code == 201
    res = admin_client.put(
        reverse(
            "dataset-actors-detail",
            kwargs={"dataset_pk": dataset_c.data["id"], "pk": dataset_c.data["actors"][0]["id"]},
        ),
        {
            "person": {"name": "hannah"},
            "organization": {"pref_label": {"fi": "CSC"}},
        },
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["person"]["name"] == "hannah"
    assert res.data["organization"]["pref_label"]["fi"] == "CSC"


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


def test_create_dataset_actor_nested_url(
    admin_client, dataset_a, dataset_actor_a, data_catalog, reference_data
):
    assert dataset_a.response.status_code == 201

    res = admin_client.post(
        f"/v3/datasets/{dataset_a.response.data['id']}/actors",
        json.dumps(dataset_actor_a.to_struct()),
        content_type="application/json",
    )
    assert res.status_code == 201


@pytest.mark.auth
def test_dataset_actor_permissions(
    requests_client, live_server, dataset, end_users, dataset_actor
):
    user1, user2, user3 = end_users
    dataset_a = dataset(
        "dataset_a.json", admin_created=False, user_token=user1.token, server_url=live_server.url
    )
    assert dataset_a.response.status_code == 201
    res1 = requests_client.post(
        f"{live_server.url}/v3/datasets/{dataset_a.dataset_id}/actors",
        json=dataset_actor(dataset_id=dataset_a.dataset_id).to_struct(),
    )
    assert res1.status_code == 201

    requests_client.headers.update({"Authorization": f"Bearer {user2.token}"})
    res2 = requests_client.post(
        f"{live_server.url}/v3/datasets/{dataset_a.dataset_id}/actors",
        json=dataset_actor(dataset_id=dataset_a.dataset_id).to_struct(),
    )
    assert res2.status_code == 403


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
    res = admin_client.put(
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
    res = admin_client.post("/v3/datasets", dataset_maximal_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_maximal_json, res.json())

    minimal_json = {
        "data_catalog": dataset_maximal_json["data_catalog"],
        "title": dataset_maximal_json["title"],
        "pid_type": "URN",
    }
    res = admin_client.put(
        f"/v3/datasets/{res.data['id']}", minimal_json, content_type="application/json"
    )
    assert res.status_code == 200

    # writable fields not in minimal_json should be cleared to falsy values
    assert list(sorted(key for key, value in res.data.items() if value)) == [
        "created",
        "data_catalog",
        "dataset_versions",
        "draft_revision",
        "id",
        "metadata_owner",
        "modified",
        "pid_type",
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
        "modified": matchers.DateTime(),  # match any datetime
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
    assert_nested_subdict(dataset_a_json, res.json())


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
    id = res.data["id"]
    res = service_client.delete(f"/v3/datasets/{id}?flush=true")
    assert res.status_code == 204
    assert not Dataset.all_objects.filter(id=id).exists()


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


@pytest.fixture
def ida_dataset(data_catalog, reference_data):
    ida_storage = factories.FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(dataset=dataset, storage=ida_storage)
    return dataset


@pytest.fixture
def ida_dataset_other(data_catalog, reference_data):
    ida_storage = factories.FileStorageFactory(storage_service="ida", csc_project="other_project")
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(dataset=dataset, storage=ida_storage)
    return dataset


@pytest.fixture
def pas_dataset(data_catalog, reference_data):
    pas_storage = factories.FileStorageFactory(storage_service="pas", csc_project="project")
    dataset = factories.DatasetFactory()
    factories.FileSetFactory(dataset=dataset, storage=pas_storage)
    return dataset


def test_filter_by_storage_service(admin_client, ida_dataset, ida_dataset_other, pas_dataset):
    res = admin_client.get(
        "/v3/datasets?storage_services=ida&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset.id), str(ida_dataset_other.id)}

    res = admin_client.get(
        "/v3/datasets?storage_services=pas&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(pas_dataset.id)}

    res = admin_client.get(
        "/v3/datasets?storage_services=ida,pas&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {
        str(pas_dataset.id),
        str(ida_dataset.id),
        str(ida_dataset_other.id),
    }


def test_filter_by_csc_project(admin_client, ida_dataset, ida_dataset_other, pas_dataset):
    res = admin_client.get(
        "/v3/datasets?csc_projects=project&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset.id), str(pas_dataset.id)}

    res = admin_client.get(
        "/v3/datasets?csc_projects=other_project&pagination=false", content_type="application/json"
    )
    assert {d["id"] for d in res.data} == {str(ida_dataset_other.id)}

    res = admin_client.get(
        "/v3/datasets?csc_projects=project,other_project&pagination=false",
        content_type="application/json",
    )
    assert {d["id"] for d in res.data} == {
        str(pas_dataset.id),
        str(ida_dataset.id),
        str(ida_dataset_other.id),
    }


def test_filter_by_has_files(
    admin_client, dataset_a, dataset_with_files, data_catalog, reference_data
):
    res = admin_client.get(
        "/v3/datasets?has_files=false&pagination=false", content_type="application/json"
    )
    assert [d["id"] for d in res.data] == [dataset_a.dataset_id]
    res = admin_client.get(
        "/v3/datasets?has_files=true&pagination=false", content_type="application/json"
    )
    assert [d["id"] for d in res.data] == [str(dataset_with_files.id)]


def test_empty_description(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_id = res.data["id"]
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"description": {"fi": "", "en": None}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["description"] == None


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
    dataset_a_json["actors"] = [
        {"person": {"name": f"Test person {i}"}, "roles": ["creator"]} for i in range(100)
    ]
    dataset_a_json["actors"][0]["roles"].append("publisher")
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201


def test_dataset_search_entry(admin_client, dataset_a_json, data_catalog, reference_data):
    """Check that search entry contains correct values from dataset."""
    dataset_a_json["other_identifiers"] = [{"notation": "doi:other_identifier"}]
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    entry = SearchEntry.objects.get(object_id=dataset_id)
    assert res.data["persistent_identifier"] in entry.title  # pid
    assert "Test dataset" in entry.title  # title
    assert "test subjects (persons)" in entry.title  # theme
    assert "Test dataset desc" in entry.description  # description
    assert "keyword another_keyword" in entry.description  # keywords
    assert "doi:other_identifier" in entry.content  # entity.notation
