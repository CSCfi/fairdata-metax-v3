import pytest
from pytest_bdd import given, then

from apps.core import factories


@pytest.fixture
@given("IDA has its own data-storage")
def ida_file_storage(ida_data_catalog):
    """

    Args:
        ida_data_catalog (): IDA-catalog instance

    TODO:
        * Associate IDA-catalog with DataStorage on Model level



    Returns:

    """
    return factories.DataStorageFactory()