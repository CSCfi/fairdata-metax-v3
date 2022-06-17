import pytest
from pytest_bdd import given

from apps.core import factories
from apps.core.models import DataCatalog


@pytest.fixture
@given("IDA has its own DataCatalog")
def ida_data_catalog() -> DataCatalog:
    return factories.DataCatalogFactory(research_dataset_schema="ida")
