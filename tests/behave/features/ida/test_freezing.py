import logging
from unittest.mock import patch, Mock

import pytest
from django.utils import timezone
from pytest_bdd import when, then, scenario

from apps.core import factories
from apps.core.models import Distribution

logger = logging.getLogger(__name__)

@pytest.mark.stub
@when("user freezes new files in IDA", target_fixture="ida_file_post_request")
def post_ida_file(mock_request):
    """This demonstrates dynamic fixture allocation in pytest-bdd.

    It also demonstrates Mocking, should be replaced with real request object when Files-API is ready

    Returns: Mocked request object

    """
    return mock_request(201)


@pytest.fixture
@when("a new distribution is created")
def created_distribution(ida_file_storage) -> Distribution:
    return factories.DistributionFactory(access_service=ida_file_storage)


@pytest.fixture
@when("the distribution has the files associated with it")
def distribution_with_files(created_distribution) -> Distribution:
    file1 = factories.FileFactory(date_frozen=timezone.now())
    file2 = factories.FileFactory(date_frozen=timezone.now())
    created_distribution.files.add(file1, file2)
    return created_distribution


@pytest.fixture
@when("distribution is associated with an IDA project")
def distribution_has_project_id(created_distribution):
    project_id = 35669
    created_distribution.project_id = Mock()
    created_distribution.project_id = project_id

    # assert created_distribution.project_id == project_id
    logger.info(f"{project_id=}")
    return created_distribution, project_id


@then("API returns OK status")
def files_have_freezing_date(ida_file_post_request):
    assert ida_file_post_request.status_code == 201
    return ida_file_post_request.status_code


@scenario("file.feature", "IDA User freezes files")
def test_file_freeze(distribution_has_project_id):
    distribution, project_id = distribution_has_project_id
    assert distribution.project_id == project_id
