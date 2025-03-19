import json
import logging
import os
from typing import Dict

import pytest
from django.db import models
from tests.utils.utils import normalize_datetime_str

from apps.core.models import Contract

logger = logging.getLogger(__name__)

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/../api/testdata/"


pytestmark = [pytest.mark.django_db]


def load_test_json(filename) -> Dict:
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def legacy_contract_json():
    return load_test_json("legacy_contract.json")


def test_create_contract(contract):
    contract.save()
    assert contract.id is not None


def test_contract_from_legacy(legacy_contract_json):
    """Test that creating contract from legacy json keeps all values from contract_json."""
    legacy_contract_json["contract_json"]["created"] = normalize_datetime_str(
        legacy_contract_json["contract_json"]["created"]
    )
    legacy_contract_json["contract_json"]["modified"] = normalize_datetime_str(
        legacy_contract_json["contract_json"]["modified"]
    )
    contract, created = Contract.create_or_update_from_legacy(legacy_contract_json)
    assert created
    to_legacy = contract.to_legacy()
    assert to_legacy["contract_json"] == legacy_contract_json["contract_json"]
    assert to_legacy["id"] == legacy_contract_json["id"]


def test_contract_from_legacy_empty_description(legacy_contract_json):
    """Test that empty description clears description."""
    legacy_contract_json["contract_json"]["description"] = "test"
    contract, created = Contract.create_or_update_from_legacy(legacy_contract_json)
    assert created
    assert contract.description == {"und": "test"}

    legacy_contract_json["contract_json"]["description"] = ""
    contract, created = Contract.create_or_update_from_legacy(legacy_contract_json)
    assert not created
    assert contract.description is None


def test_contract_from_legacy_too_big_quota(legacy_contract_json):
    """Test that quota value is clamped to max bigint value (needed for some legacy test data)."""
    legacy_contract_json["contract_json"]["quota"] = 1.23e25
    contract, created = Contract.create_or_update_from_legacy(legacy_contract_json)
    assert created
    assert contract.quota == models.BigIntegerField.MAX_BIGINT
