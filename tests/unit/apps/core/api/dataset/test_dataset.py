import json
import logging
from unittest.mock import ANY

import pytest
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers

from apps.core.models import OtherIdentifier
from apps.core.models.concepts import IdentifierType
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset(admin_client, dataset_a_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)


def test_update_dataset(
    admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = admin_client.put(f"/v3/datasets/{id}", dataset_b_json, content_type="application/json")
    assert_nested_subdict(dataset_b_json, res.data)


def test_filter_pid(admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = admin_client.get("/v3/datasets?persistent_identifier=some_pid")
    assert res.data["count"] == 1


def test_search_pid(admin_client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = admin_client.get("/v3/datasets?search=some_pid")
    assert res.data["count"] == 1


def test_create_dataset_invalid_catalog(admin_client, dataset_a_json):
    dataset_a_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-does-not-exist"
    response = admin_client.post("/v3/publishers", dataset_a_json, content_type="application/json")
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
    }


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
        "user": {"username": "metax-user-a"},
    }
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")

    assert res.status_code == 201


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
            "organization": {"pref_label": {"fi": "CSC"}, "in_scheme": "https://testischeema.fi"},
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
    }
    res = admin_client.put(
        f"/v3/datasets/{res.data['id']}", minimal_json, content_type="application/json"
    )
    assert res.status_code == 200

    # writable fields not in minimal_json should be cleared to falsy values
    assert list(sorted(key for key, value in res.data.items() if value)) == [
        "created",
        "data_catalog",
        "id",
        "modified",
        "state",
        "title",
    ]


def test_dataset_patch_maximal_and_minimal(
    admin_client, dataset_maximal_json, reference_data, data_catalog
):
    res = admin_client.post("/v3/datasets", dataset_maximal_json, content_type="application/json")
    assert res.status_code == 201
    maximal_data = res.json()

    minimal_json = {
        "title": {"en": "new title"},
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
    }


def test_dataset_put_remove_fileset(
    admin_client, dataset_maximal_json, reference_data, data_catalog
):
    FileStorageFactory(storage_service="ida", project="project")
    dataset_maximal_json["fileset"] = {
        "storage_service": "ida",
        "project": "project",
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


def test_dataset_metadata_download_datacite(
    admin_client, dataset_a_json, dataset_a, reference_data, data_catalog
):
    pytest.xfail("DataCite XML implementation missing")
    assert dataset_a.response.status_code == 201
    id = dataset_a.data["id"]
    res = admin_client.get(f"/v3/datasets/{id}/metadata-download?format=datacite")
    assert res.status_code == 200
    # check dataset_a data in res.data
    assert res.headers.get("Content-Disposition") == f"attachment; filename='{id}-metadata.xml'"


def test_dataset_metadata_download_invalid_id(admin_client):
    res = admin_client.get(f"/v3/datasets/invalid_id/metadata-download")
    assert res.status_code == 404
    assert res.headers.get("Content-Disposition") == None
    assert res.data == "Dataset not found."
