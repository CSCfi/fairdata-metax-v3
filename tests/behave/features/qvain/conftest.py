import logging

import pytest
from django.forms import model_to_dict
from django.utils import timezone
from pytest_bdd import given, then, when

from apps.core.factories import DatasetFactory
from apps.core.models import DataCatalog, Dataset
from apps.files.factories import FileFactory
from apps.users.factories import MetaxUserFactory

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_qvain_dataset_with_files_request(qvain_user, frozen_files_in_ida, mock_request):
    def _mock_qvain_dataset_with_files_request(status_code, published):
        request = mock_request(status_code)
        request.published = published
        request.user = qvain_user
        request.files = frozen_files_in_ida
        return request

    yield _mock_qvain_dataset_with_files_request
    raise NotImplementedError


@pytest.fixture
@given("user has frozen files in IDA")
def frozen_files_in_ida():
    """When files are frozen in IDA, new File Model Objects are created for the IDA-project in Metax"""
    files = FileFactory.create_batch(3, frozen=timezone.now())
    return files


@pytest.fixture
@when("user publishes a new dataset in Qvain")
def qvain_publish_request(mock_qvain_dataset_with_files_request):
    """Makes API-Request to Dataset API with Dataset information

    Returns: API Request Response for Qvain

    """
    request = mock_qvain_dataset_with_files_request(status_code=201, published=True)
    yield request
    raise NotImplementedError


@pytest.fixture
@when("new published dataset is created in IDA data-catalog with persistent identifier")
def published_dataset(ida_data_catalog: DataCatalog, qvain_publish_request, faker) -> Dataset:
    """

    TODO:
        * Research Dataset should be generated in the qvain_publish_request step instead of using Factory Class
        * This step should do an assert instead of being a fixture

    Args:
        qvain_publish_request (): Request object from Qvain
        ida_data_catalog (): IDA DataCatalog

    Returns: Research Dataset object

    """

    dataset = DatasetFactory(
        data_catalog=ida_data_catalog,
        issued=timezone.now(),
        persistent_identifier=faker.uuid4(),
    )
    yield dataset
    raise NotImplementedError


@pytest.fixture
def qvain_user(faker):
    user = MetaxUserFactory(username="test_user", password=faker.password())
    return user
