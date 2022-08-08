from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from pytest_bdd import given

from apps.core import factories
from apps.core.models import DataCatalog


@pytest.fixture
@given("IDA has its own data-catalog")
def ida_data_catalog() -> DataCatalog:
    return factories.DataCatalogFactory(research_dataset_schema="ida")


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
