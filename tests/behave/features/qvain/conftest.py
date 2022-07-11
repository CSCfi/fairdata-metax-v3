import logging

import pytest

from django.forms import model_to_dict
from django.utils import timezone
from pytest_bdd import given, when, then

from apps.core.factories import (
    FileFactory,
    DistributionFactory,
    ResearchDatasetFactory,
)
from apps.core.models import ResearchDataset, Distribution, DataCatalog

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_qvain_dataset_with_files_request(
    qvain_user, frozen_distribution, mock_request
):
    def _mock_qvain_dataset_with_files_request(status_code, published):
        request = mock_request(status_code)
        request.published = published
        request.user = qvain_user
        request.files = frozen_distribution.files.all()[:2]
        return request

    return _mock_qvain_dataset_with_files_request


@pytest.fixture
@given("user has frozen files in IDA")
def frozen_files_in_ida():
    """When files are frozen in IDA, new File Model Objects are created for the IDA-project in Metax"""
    files = FileFactory.create_batch(3, date_frozen=timezone.now())
    return files


@pytest.fixture
@given("there is distribution from the freeze")
def frozen_distribution(frozen_files_in_ida) -> Distribution:
    """Distribution generated from freeze action in IDA"""
    distribution = DistributionFactory()
    distribution.files.add(*frozen_files_in_ida)
    return distribution


@pytest.fixture
@when("user publishes a new dataset in Qvain")
def qvain_publish_request(frozen_distribution, mock_qvain_dataset_with_files_request):
    """Makes API-Request to Dataset API with Dataset information

    Returns: API Request Response for Qvain

    """
    request = mock_qvain_dataset_with_files_request(status_code=201, published=True)
    return request


@pytest.fixture
@then("new published dataset is created in IDA data-catalog with persistent identifier")
def published_dataset(
    ida_data_catalog: DataCatalog, qvain_publish_request, faker
) -> ResearchDataset:
    """

    TODO: Research Dataset should be generated in the qvain_publish_request step instead of using Factory Class
    TODO: This step should do an assert instead of being a fixture

    Args:
        qvain_publish_request (): Request object from Qvain
        ida_data_catalog (): IDA DataCatalog

    Returns: Research Dataset object

    """

    dataset = ResearchDatasetFactory(
        data_catalog=ida_data_catalog,
        release_date=timezone.now(),
        persistent_identifier=faker.uuid4(),
    )
    assert dataset.id is not None
    return dataset


@when("user publishes new version of dataset in Qvain")
def new_dataset_version_request(mock_qvain_dataset_with_files_request):
    return mock_qvain_dataset_with_files_request(status_code=200, published=True)


@pytest.fixture
@then("edited dataset is saved as a new version of the dataset")
def created_new_dataset_version(published_dataset):
    """Should test versioning of dataset

    Current very basic versioning scheme (Research Dataset has foreign keys next, first, last, and so on..)  is
    probably going to be replaced with django-simple-history library. For some reason the foreign key relations work
    funny when foreign key points to self AND the model has OneToOne relation. Solution could be to drop the
    CatalogRecord entirely, as all of its fields can be in ResearchDataset Model.

    Args:
        created_catalog_record (): Research Dataset Object

    Returns: New instance of the Research Dataset with the modified fields

    """
    original_fields = model_to_dict(published_dataset)
    logger.info(original_fields)
    del original_fields["catalogrecord_ptr"]
    del original_fields["data_catalog"]
    del original_fields["language"]
    new_version = ResearchDataset(**original_fields)
    new_version.data_catalog = published_dataset.data_catalog
    new_version.title = {"en": "new title"}

    new_version.replaces = published_dataset
    new_version.save()

    # Loads RelatedObjectManager instead of foreign key object
    # assert new_version.replaces == published_dataset

    return new_version


@then("previous dataset version is still available as previous version")
def prev_dataset_exists(created_new_dataset_version, published_dataset):
    raise NotImplementedError


@then("Previous version is referenced in current version")
def current_dataset_has_prev_dataset_reference():
    raise NotImplementedError
