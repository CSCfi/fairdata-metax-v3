import pytest
from pytest_bdd import given, then

from apps.core import factories


@pytest.fixture
@given("IDA has its own data-storage")
def ida_file_storage(ida_data_catalog):
    return factories.DataStorageFactory()


@then("Distribution will have IDA as DataStorage")
def distribution_has_ida_file_storage():
    raise NotImplementedError
