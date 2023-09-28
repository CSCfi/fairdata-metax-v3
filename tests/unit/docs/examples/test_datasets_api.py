import logging

import pytest

from apps.core.models import Dataset
from tests.unit.docs.examples.conftest import load_test_json

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
):
    data = {
        "title": {"fi": "datasetti"},
        "language": language_json["language"],
        "data_catalog": data_catalog.id,
        "access_rights": access_rights_json["access_rights"],
        "actors": actors_json["actors"],
        "spatial": [spatial_json],
    }
    res = client.post("/v3/datasets", data, content_type="application/json")
    assert res.status_code == 201
    assert len(res.data["language"]) == 2
    assert len(res.data["actors"]) == 2
    assert len(res.data["spatial"]) == 1
    assert (
        res.data["access_rights"]["description"]
        == access_rights_json["access_rights"]["description"]
    )


def test_modify_dataset(
    client, data_catalog, reference_data, v1_v3_dataset_v3_json, dataset_v3_modify_json
):
    res = client.post("/v3/datasets", v1_v3_dataset_v3_json, content_type="application/json")
    assert res.status_code == 201

    put = client.put(
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
