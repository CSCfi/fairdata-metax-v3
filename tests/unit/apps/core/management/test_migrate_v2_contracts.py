import os
from io import StringIO

import pytest
from django.core.management import call_command
from tests.utils import matchers

from apps.core.models.contract import Contract

from .conftest import get_mock_data

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.adapter,
    pytest.mark.usefixtures("data_catalog", "reference_data", "v2_integration_settings"),
]


test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/"


@pytest.fixture
def mock_endpoint_contracts(requests_mock):
    contracts = get_mock_data("legacy_contracts.json")
    nonremoved = [c for c in contracts if not c["removed"]]
    removed = [c for c in contracts if c["removed"]]

    return {
        "removed": requests_mock.get(
            url="https://metax-v2-test/rest/v2/contracts?ordering=id&removed=true",
            json={"count": len(removed), "results": removed},
        ),
        "nonremoved": requests_mock.get(
            url="https://metax-v2-test/rest/v2/contracts?ordering=id&removed=false",
            json={"count": len(nonremoved), "results": nonremoved},
        ),
    }


def test_migrate_command(mock_response, mock_endpoint_contracts):
    out = StringIO()
    err = StringIO()
    call_command("migrate_v2_contracts", stdout=out, stderr=err, use_env=True)
    assert [
        (c.title["und"], c.id, c.legacy_id, c.removed)
        for c in Contract.all_objects.order_by("legacy_id").all()
    ] == [
        ("Testisopimus", "urn:uuid:0d32393b-1be2-454e-98ff-100000000001", 123, None),
        ("Testisopimus 2", "urn:uuid:0d32393b-1be2-454e-98ff-100000000002", 124, None),
        (
            "Poistettu sopimus",
            "urn:uuid:0d32393b-1be2-454e-98ff-100000000003",
            125,
            matchers.DateTime(),
        ),
    ]
    assert len(err.readlines()) == 0
    assert mock_endpoint_contracts["nonremoved"].call_count == 1
    assert mock_endpoint_contracts["removed"].call_count == 1


def test_migrate_missing_config():
    err = StringIO()
    call_command("migrate_v2_contracts", stderr=err)
    assert "Missing Metax V2 configuration" in err.getvalue()
