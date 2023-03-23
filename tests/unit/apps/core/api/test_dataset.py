import logging

import pytest
from tests.utils import assert_nested_subdict

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_create_dataset(client, dataset_a_json, data_catalog, reference_data):
    res = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)


@pytest.mark.django_db
def test_update_dataset(client, dataset_a_json, dataset_b_json, data_catalog, reference_data):
    res = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    res = client.put(f"/rest/v3/datasets/{id}", dataset_b_json, content_type="application/json")
    assert_nested_subdict(dataset_b_json, res.data)


@pytest.mark.django_db
def test_create_dataset_invalid_catalog(client, dataset_a_json):
    dataset_a_json["data_catalog"] = "urn:nbn:fi:att:data-catalog-does-not-exist"
    response = client.post("/rest/v3/publishers", dataset_a_json, content_type="application/json")
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

    response = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["language"] == [expected_error]


@pytest.mark.django_db
def test_delete_dataset(client, dataset_a_json, data_catalog, reference_data):
    res = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")
    id = res.data["id"]
    assert res.status_code == 201
    assert_nested_subdict(dataset_a_json, res.data)
    res = client.delete(f"/rest/v3/datasets/{id}")
    assert res.status_code == 204


@pytest.mark.django_db
def test_list_datasets_with_ordering(
    client, dataset_a_json, dataset_b_json, data_catalog, reference_data
):
    res = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")
    dataset_a_id = res.data["id"]
    client.post("/rest/v3/datasets", dataset_b_json, content_type="application/json")
    client.put(
        f"/rest/v3/datasets/{dataset_a_id}",
        dataset_a_json,
        content_type="application/json",
    )
    res = client.get("/rest/v3/datasets?ordering=created")
    assert_nested_subdict(
        {0: dataset_a_json, 1: dataset_b_json}, dict(enumerate((res.data["results"])))
    )

    res = client.get("/rest/v3/datasets?ordering=modified")
    assert_nested_subdict(
        {0: dataset_b_json, 1: dataset_a_json}, dict(enumerate((res.data["results"])))
    )


@pytest.mark.django_db
def test_create_dataset_with_metadata_owner(client, dataset_a_json, data_catalog, reference_data):
    dataset_a_json["metadata_owner"] = {
        "organization": "organization-a.fi",
        "user": {"username": "metax-user-a"},
    }
    res = client.post("/rest/v3/datasets", dataset_a_json, content_type="application/json")

    assert res.status_code == 201
