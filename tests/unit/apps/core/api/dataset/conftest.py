import pytest

from tests.unit.apps.core.api.json_models import DatasetActor, Actor, Organization
from rest_framework.reverse import reverse

from tests.unit.apps.core.api.conftest import load_test_json


@pytest.fixture
def dataset_a_json():
    return load_test_json("dataset_a.json")


@pytest.fixture
def dataset_b_json():
    return load_test_json("dataset_b.json")


@pytest.fixture
def dataset_c_json():
    return load_test_json("dataset_c.json")


@pytest.fixture
def legacy_dataset_a_json():
    return load_test_json("legacy_dataset_a.json")


@pytest.fixture
def dataset_access_right_error_json():
    return load_test_json("access_right_error.json")


@pytest.fixture
def dataset_a(client, dataset_a_json, data_catalog, reference_data):
    return client.post("/v3/datasets", dataset_a_json, content_type="application/json")


@pytest.fixture
def dataset_b(client, dataset_b_json, data_catalog, reference_data):
    return client.post("/v3/datasets", dataset_b_json, content_type="application/json")


@pytest.fixture
def dataset_c(client, dataset_c_json, data_catalog, reference_data):
    return client.post("/v3/datasets", dataset_c_json, content_type="application/json")


@pytest.fixture
def dataset_actor_a(dataset_a):
    return DatasetActor(
        dataset=dataset_a.data["id"],
        actor=Actor(
            name="teppo",
            organization=Organization(
                pref_label={"fi": "CSC"}, in_scheme="https://joku.scheme.fi"
            ),
        ),
        role="creator",
    )


@pytest.fixture
def legacy_dataset_a(client, data_catalog, reference_data, legacy_dataset_a_json):
    return client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )
