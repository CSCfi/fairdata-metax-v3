import logging

import pytest
from django.utils.dateparse import parse_datetime
from tests.unit.docs.examples.conftest import load_test_json
from tests.utils import assert_nested_subdict

from apps.core.models import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.docs]


@pytest.fixture
def access_rights_json():
    return load_test_json("dataset_api/access_rights.json")


@pytest.fixture
def language_json():
    return load_test_json("dataset_api/language.json")


@pytest.fixture
def actors_json():
    return load_test_json("dataset_api/actors.json")


@pytest.fixture
def spatial_json():
    return load_test_json("dataset_api/spatial.json")


@pytest.fixture
def temporal_json():
    return load_test_json("dataset_api/temporal.json")


@pytest.fixture
def remote_resources_json():
    return load_test_json("dataset_api/remote_resources.json")


@pytest.fixture
def dataset_v3_modify_json():
    return load_test_json("dataset_api/modify-dataset.json")


def test_dataset_snippets(
    client,
    data_catalog,
    reference_data,
    language_json,
    access_rights_json,
    actors_json,
    spatial_json,
    temporal_json,
    remote_resources_json,
):
    data = {
        "title": {"fi": "datasetti"},
        "language": language_json["language"],
        "data_catalog": data_catalog.id,
        "access_rights": access_rights_json["access_rights"],
        "actors": actors_json["actors"],
        "spatial": [spatial_json],
        "temporal": temporal_json["temporal"],
        "remote_resources": remote_resources_json["remote_resources"],
    }
    res = client.post("/v3/datasets", data, content_type="application/json")
    assert res.status_code == 201
    assert len(res.data["language"]) == 2
    assert len(res.data["actors"]) == 2

    # can't compare datetimes directly due to time zones, need to parse first
    assert len(res.data["temporal"]) == 2
    assert parse_datetime(temporal_json["temporal"][0]["start_date"]) == parse_datetime(
        res.data["temporal"][0]["start_date"]
    )
    assert parse_datetime(temporal_json["temporal"][0]["end_date"]) == parse_datetime(
        res.data["temporal"][0]["end_date"]
    )
    assert parse_datetime(temporal_json["temporal"][1]["start_date"]) == parse_datetime(
        res.data["temporal"][1]["start_date"]
    )
    assert res.data["temporal"][1]["end_date"] == None

    assert len(res.data["spatial"]) == 1
    assert_nested_subdict(spatial_json, res.data["spatial"][0])
    assert (
        res.data["access_rights"]["description"]
        == access_rights_json["access_rights"]["description"]
    )

    assert_nested_subdict(
        remote_resources_json["remote_resources"],
        res.json()["remote_resources"],
        check_list_length=True,
    )


def test_modify_dataset(
    client, data_catalog, reference_data, v1_v3_dataset_v3_json, dataset_v3_modify_json
):
    res = client.post("/v3/datasets", v1_v3_dataset_v3_json, content_type="application/json")
    assert res.status_code == 201

    put = client.patch(
        f"/v3/datasets/{res.data['id']}", dataset_v3_modify_json, content_type="application/json"
    )
    dataset = Dataset.objects.get(id=res.data["id"])
    assert put.status_code == 200
    assert dataset.title == put.data["title"]
    assert dataset.description == put.data["description"]
    assert dataset.language.all().count() == len(put.data["language"])
    assert dataset.language.filter(url="http://lexvo.org/id/iso639-3/eng").count() == 1
    assert dataset.persistent_identifier == res.data["persistent_identifier"]
    assert dataset.cumulative_state == 2
    assert dataset.field_of_science.all().count() == len(res.data["field_of_science"])
