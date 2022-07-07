import pytest
from django.contrib.auth import get_user_model
import faker
from pytest_bdd import given

from apps.core import factories
from apps.core.models import DataCatalog

fake = faker.Faker()


@pytest.fixture
@given("IDA has its own DataCatalog")
def ida_data_catalog() -> DataCatalog:
    return factories.DataCatalogFactory(research_dataset_schema="ida")


@pytest.fixture
def qvain_user():
    user, created = get_user_model().objects.get_or_create(
        username="test_user", password=fake.password()
    )
    return user
