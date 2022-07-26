import logging
from unittest.mock import patch, Mock

import pytest
from django.utils import timezone
from pytest_bdd import when, then, scenario

from apps.core import factories
from apps.core.models import Distribution

logger = logging.getLogger(__name__)


@pytest.fixture
@when("user freezes new files in IDA")
def post_ida_file(mock_request):
    """

    TODO:
        * should be replaced with real request object when Files-API is ready

    Returns: Mocked request object

    """

    yield mock_request(201)
    raise NotImplementedError



@pytest.fixture
@when("a new distribution is created")
def created_distribution(ida_file_storage) -> Distribution:
    """

    Args:
        ida_file_storage (FileStorage): FileStorage instance

    Returns:
        Distribution: Distribution from freezing action on IDA

    """
    return factories.DistributionFactory(access_service=ida_file_storage)


@pytest.fixture
@when("the distribution has the files associated with it")
def distribution_with_files(created_distribution) -> Distribution:
    """Ensure files are associated with the distribution

    Args:
        created_distribution (Distribution): Distribution from freezing action on IDA

    Returns:
        Distribution: Frozen Distribution with files

    """
    file1 = factories.FileFactory(date_frozen=timezone.now())
    file2 = factories.FileFactory(date_frozen=timezone.now())
    created_distribution.files.add(file1, file2)
    return created_distribution


@pytest.fixture
@when("distribution is associated with an IDA project")
def distribution_with_project_id(distribution_with_files):
    """Ensure Distribution has IDA project id association

    Args:
        distribution_with_files (): Distribution from freezing action on IDA

    Returns:

    """
    project_id = 35669
    distribution_with_files.project_id = Mock()
    distribution_with_files.project_id = project_id


    logger.info(f"{project_id=}")

    yield distribution_with_files, project_id
    raise NotImplementedError


@then("API returns OK status")
def files_have_freezing_date(post_ida_file):
    """

    Args:
        ida_file_post_request (): POST-request object from IDA to Files API

    Returns:

    """
    assert post_ida_file.status_code == 201



@pytest.mark.xfail(raises=NotImplementedError)
@scenario("file.feature", "IDA User freezes files")
def test_file_freeze(distribution_with_project_id):
    distribution, project_id = distribution_with_project_id
    logger.info(f"{distribution=}, {project_id=}")
    assert distribution.project_id == project_id
