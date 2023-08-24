import json
import logging
from unittest.mock import ANY

import pytest
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict

from apps.core.models import OtherIdentifier
from apps.core.models.concepts import IdentifierType

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset(client, dataset_a_json, data_catalog, reference_data):
    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)


def test_update_dataset(client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = client.put(f"/v3/datasets/{id}", dataset_b_json, content_type="application/json")
    assert_nested_subdict(dataset_b_json, res.data)


def test_filter_pid(client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = client.get("/v3/datasets?persistent_identifier=some_pid")
    assert res.data["count"] == 1


def test_search_pid(client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    dataset_a_json["persistent_identifier"] = "some_pid"
    dataset_b_json.pop("persistent_identifier", None)
    client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    res = client.get("/v3/datasets?search=some_pid")
    assert res.data["count"] == 1


def test_create_dataset_invalid_catalog(client, dataset_a_json):
    dataset_a_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-does-not-exist"
    response = client.post("/v3/publishers", dataset_a_json, content_type="application/json")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "value,expected_error",
    [
        ([{"url": "non_existent"}], "Entries not found for given URLs: non_existent"),
        ([{"foo": "bar"}], "'url' field must be defined for each object in the list"),
        (["FI"], "Each item in the list must be an object with the field 'url'"),
        ("FI", 'Expected a list of items but got type "str".'),
    ],
)
def test_create_dataset_invalid_language(client, dataset_a_json, value, expected_error):
    """
    Try creating a dataset with an improperly formatted 'language' field.
    Each error case has a corresponding error message.
    """
    dataset_a_json["language"] = value

    response = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["language"] == [expected_error]


def test_delete_dataset(client, dataset_a_json, data_catalog, reference_data):
    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)
    res = client.delete(f"/v3/datasets/{id}")
    assert res.status_code == 204


def test_list_datasets_with_ordering(
    client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_a_id = res.data["id"]
    client.post("/v3/datasets", dataset_b_json, content_type="application/json")
    client.put(
        f"/v3/datasets/{dataset_a_id}",
        dataset_a_json,
        content_type="application/json",
    )
    res = client.get("/v3/datasets?ordering=created")
    assert_nested_subdict(
        {0: dataset_a_json, 1: dataset_b_json}, dict(enumerate((res.data["results"])))
    )

    res = client.get("/v3/datasets?ordering=modified")
    assert_nested_subdict(
        {0: dataset_b_json, 1: dataset_a_json}, dict(enumerate((res.data["results"])))
    )


def test_list_datasets_with_default_pagination(client, dataset_a, dataset_b):
    res = client.get(reverse("dataset-list"))
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [ANY, ANY],
    }


def test_list_datasets_with_pagination(client, dataset_a, dataset_b):
    res = client.get(reverse("dataset-list"), {"pagination": "true"})
    assert res.status_code == 200
    assert res.data == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [ANY, ANY],
    }


def test_list_datasets_with_no_pagination(client, dataset_a, dataset_b):
    res = client.get(reverse("dataset-list"), {"pagination": "false"})
    assert res.status_code == 200
    assert res.data == [ANY, ANY]


def test_create_dataset_with_metadata_owner(client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["metadata_owner"] = {
        "organization": "organization-a.fi",
        "user": {"username": "metax-user-a"},
    }
    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")

    assert res.status_code == 201


def test_create_dataset_with_actor(client, dataset_c, data_catalog, reference_data):
    assert dataset_c.status_code == 201


def test_create_dataset_actor_nested_url(
    client, dataset_a, dataset_actor_a, data_catalog, reference_data
):
    assert dataset_a.status_code == 201

    res = client.post(
        f"/v3/datasets/{dataset_a.data['id']}/actors",
        json.dumps(dataset_actor_a.to_struct()),
        content_type="application/json",
    )
    assert res.status_code == 201


@pytest.mark.django_db
def test_create_dataset_with_other_identifiers(
    client, dataset_a_json, data_catalog, reference_data
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

    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert len(res.data["other_identifiers"]) == 3


@pytest.mark.django_db
def test_update_dataset_with_other_identifiers(
    client, dataset_a_json, data_catalog, reference_data
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

    res = client.post("/v3/datasets", dataset_a_json, content_type="application/json")
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
    res = client.put(f"/v3/datasets/{ds_id}", dataset_a_json, content_type="application/json")
    assert res.status_code == 200
    assert len(res.data["other_identifiers"]) == 4
    assert_nested_subdict(dataset_a_json["other_identifiers"], res.data["other_identifiers"])

    # Assert that the old other_identifiers don't exist in the db anymore
    new_count = OtherIdentifier.available_objects.all().count()
    assert new_count == 4
