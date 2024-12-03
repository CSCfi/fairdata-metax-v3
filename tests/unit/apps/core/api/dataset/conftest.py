from dataclasses import dataclass, field

import pytest
from rest_framework.reverse import reverse
from tests.unit.apps.core.api.conftest import load_test_json
from tests.unit.apps.core.api.json_models import DatasetActor, Organization, Person


@dataclass
class DatasetData:
    json_file_name: str
    json_payload: dict = field(default_factory=dict)
    response = None
    dataset_id = None

    def __post_init__(self):
        self.json_payload = load_test_json(self.json_file_name)

    def json(self):
        return self.json_payload


@pytest.fixture
def dataset_list_url():
    return reverse("dataset-list")


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
def dataset_d_json():
    return load_test_json("dataset_d.json")


@pytest.fixture
def dataset_maximal_json():
    return load_test_json("dataset_maximal.json")


@pytest.fixture
def legacy_dataset_a_json():
    return load_test_json("legacy_dataset_a.json")


@pytest.fixture
def legacy_dataset_b_json():
    return load_test_json("legacy_dataset_b.json")


@pytest.fixture
def dataset_access_right_error_json():
    return load_test_json("access_right_error.json")


@pytest.fixture
def dataset(admin_client, data_catalog, reference_data, requests_client, dataset_list_url):
    def _dataset(
        json_file_name,
        endpoint_url=dataset_list_url,
        client=admin_client,
        admin_created=True,
        create=True,
        user_token=None,
        server_url=None,
    ):
        data = DatasetData(json_file_name)

        if admin_created and create:
            data.response = client.post(endpoint_url, data.json(), content_type="application/json")
            data.dataset_id = data.response.data["id"]
        elif admin_created is False and create:
            full_url = f"{server_url}{endpoint_url}"
            requests_client.headers.update({"Authorization": f"Bearer {user_token}"})
            data.response = requests_client.post(full_url, json=data.json())
            data.dataset_id = data.response.json()["id"]
        return data

    return _dataset


@pytest.fixture
def dataset_a(
    dataset_a_json,
    data_catalog,
    reference_data,
    end_users,
    dataset,
):
    return dataset("dataset_a.json")


@pytest.fixture
def dataset_b(admin_client, dataset_b_json, data_catalog, reference_data):
    return admin_client.post("/v3/datasets", dataset_b_json, content_type="application/json")


@pytest.fixture
def dataset_c(admin_client, dataset_c_json, data_catalog, reference_data):
    return admin_client.post("/v3/datasets", dataset_c_json, content_type="application/json")


@pytest.fixture
def dataset_actor():
    def _dataset_actor(
        dataset_id, role=["creator"], person_name="teppo", org_pref_label={"fi": "CSC"}
    ):
        return DatasetActor(
            dataset=dataset_id,
            person=Person(name=person_name),
            organization=Organization(pref_label=org_pref_label),
            role=role,
        )

    return _dataset_actor


@pytest.fixture
def dataset_actor_a(dataset_a):
    return DatasetActor(
        dataset=dataset_a.response.data["id"],
        person=Person(name="teppo"),
        organization=Organization(pref_label={"fi": "CSC"}),
        roles=["creator"],
    )


@pytest.fixture
def legacy_dataset_a(admin_client, data_catalog_att, reference_data, legacy_dataset_a_json):
    return admin_client.post(
        reverse("migrated-dataset-list"), legacy_dataset_a_json, content_type="application/json"
    )


@pytest.fixture
def entity_json():
    return load_test_json("entity.json")


@pytest.fixture
def pid_update_payload():
    return load_test_json("pid_update_payload.json")