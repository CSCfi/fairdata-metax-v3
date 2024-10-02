import json
import os
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from pytest_bdd import given

from apps.core import factories
from apps.core.models import DataCatalog

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"


def load_test_json(filename):
    with open(test_data_path + filename) as json_file:
        data = json.load(json_file)
    return data


@pytest.fixture
def ida_files_json():
    return load_test_json("ida_files.json")


@pytest.fixture
@given("IDA has its own data-catalog")
def ida_data_catalog() -> DataCatalog:
    return factories.DataCatalogFactory(allowed_pid_types=["URN", "DOI"])


@pytest.fixture
def qvain_user(faker):
    user, created = get_user_model().objects.get_or_create(
        username="test_user", password=faker.password()
    )
    return user


@pytest.fixture
def mock_request():
    def _mock_request(status_code):
        request = MagicMock()
        request.status_code = status_code
        return request

    return _mock_request
