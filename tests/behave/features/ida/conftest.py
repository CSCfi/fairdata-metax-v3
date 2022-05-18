import pytest
from pytest_bdd import scenario, given, when, then
from unittest.mock import MagicMock, patch

from apps.core import factories
from apps.core.models import Distribution


@pytest.fixture
@given("IDA has its own DataStorage")
def ida_file_storage(ida_data_catalog):
    return factories.DataStorageFactory()


@when("User freezes new files in IDA", target_fixture="ida_file_post_request")
def post_ida_file():
    """This demonstrates dynamic fixture allocation in pytest-bdd.

    It also demonstrates Mocking, should be replaced with real request object when Files-API is ready

    Returns: Mocked request object

    """
    request = MagicMock()
    request.status_code = 201
    return request


@pytest.fixture
@then("new Distribution is saved to database")
def created_distribution(ida_file_storage) -> Distribution:
    return factories.DistributionFactory()


@pytest.fixture
@then("Files are saved as part of Distribution")
def distribution_with_files(created_distribution) -> Distribution:
    file1 = factories.FileFactory()
    file2 = factories.FileFactory()
    created_distribution.files.add(file1, file2)
    return created_distribution


@then("Distribution will have an IDA project identifier")
def distribution_has_project_id(created_distribution):
    raise NotImplementedError


@then("Files and Distribution will have an freezing date")
def files_have_freezing_date(distribution_with_files):
    raise NotImplementedError


@then("Distribution will have IDA as DataStorage")
def distribution_has_ida_file_storage():
    raise NotImplementedError


@when("User unfreezes file in IDA")
def user_unfreeze_request():
    raise NotImplementedError


@then("The file is marked as deleted")
def mark_files_deleted():
    raise NotImplementedError


@then("Any Dataset with the file is marked as deprecated")
def deprecate_dataset():
    pass
