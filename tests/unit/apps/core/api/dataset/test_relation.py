import logging

import pytest
from tests.utils import assert_nested_subdict

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_entity_relation(admin_client, dataset_a_json, entity_json, data_catalog, reference_data):
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    relation = {
        "entity": entity_json,
        "relation_type": {"url": "http://purl.org/dc/terms/relation"},
    }
    res = admin_client.patch(
        f"/v3/datasets/{res.data['id']}",
        {"relation": [relation]},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert_nested_subdict([relation], res.data["relation"])
