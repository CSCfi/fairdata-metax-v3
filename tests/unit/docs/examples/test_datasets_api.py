import pytest
from tests.unit.docs.examples.conftest import load_test_json

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
