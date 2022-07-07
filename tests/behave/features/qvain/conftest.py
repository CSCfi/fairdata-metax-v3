import logging
from unittest.mock import MagicMock, patch

import faker
import pytest

from django.forms import model_to_dict
from django.utils import timezone
from pytest_bdd import given, when, then

from apps.core.factories import (
    FileFactory,
    DistributionFactory,
    ResearchDatasetFactory,
)
from apps.core.models import ResearchDataset

logger = logging.getLogger(__name__)

fake = faker.Faker()


@pytest.fixture
def mock_qvain_dataset_request(qvain_user, frozen_distribution):
    def _mock_qvain_dataset_request(status_code, published):
        request = MagicMock()
        request.status_code = status_code
        request.published = published
        request.user = qvain_user
        request.files = frozen_distribution.files.all()[:2]
        return request

    return _mock_qvain_dataset_request


@pytest.fixture
@given("I have frozen files in IDA")
def frozen_files_in_ida():
    """When files are frozen in IDA, new File Model Objects are created for the IDA-project in Metax"""
    files = FileFactory.create_batch(3, date_frozen=timezone.now())
    return files


@pytest.fixture
@given("There is distribution from the freeze")
def frozen_distribution(frozen_files_in_ida):
    """Distribution generated from freeze action in IDA

    It is still unclear if freeze action should generate new distribution every time
    """
    distribution = DistributionFactory()
    distribution.files.add(*frozen_files_in_ida)
    return distribution


@pytest.fixture
@pytest.mark.stub
@when("I publish a new dataset in Qvain")
def qvain_publish_request(frozen_distribution, mock_qvain_dataset_request):
    """Makes API-Request to Dataset API with Dataset information

    Returns: API Request Response for Qvain

    """
    request = mock_qvain_dataset_request(status_code=201, published=True)
    return request


@pytest.fixture
@then("New published Dataset is saved to database")
def created_catalog_record(ida_data_catalog, qvain_publish_request) -> ResearchDataset:
    """CatalogRecord is distinct object, separate from Dataset

    TODO: Research Dataset should be generated in the qvain_publish_request step instead of using Factory Class
    TODO: This step should do an assert instead of being a fixture

    Args:
        ida_data_catalog (): IDA DataCatalog

    Returns: Research Dataset object

    """

    dataset = ResearchDatasetFactory(
        data_catalog=ida_data_catalog, release_date=timezone.now()
    )
    assert dataset.id is not None
    return dataset


@pytest.mark.stub
@patch("apps.core.models.CatalogRecord.creator")
@then("The User is saved as creator to the Catalog Record")
def catalog_record_creator(qvain_publish_request):
    """Should be implemented at the same time as user model"""

    created_catalog_record.creator = qvain_publish_request.user

    assert qvain_publish_request.user is created_catalog_record.creator


@pytest.fixture
@then("New Distribution is derived from frozen files Distribution")
def derived_distribution(frozen_distribution, qvain_publish_request):
    """Frozen distribution is generated when files are frozen in IDA

    If the dataset files are different from frozen distribution, new distribution should be created.
    This new distribution would reference the frozen distribution. This is possible if Distribution object has
    ForeignKey to self.

    It is currently unclear if new distribution should be created for every freeze operation.
    """
    derived_distribution = DistributionFactory()
    if set(frozen_distribution.files.all()) != set(qvain_publish_request.files.all()):
        derived_distribution.files.set(
            frozen_distribution.files.intersection(qvain_publish_request.files)
        )
    else:
        derived_distribution.files.set(frozen_distribution.files.all())
    assert (
        frozen_distribution.files.intersection(qvain_publish_request.files).count()
        == derived_distribution.files.count()
    )
    return derived_distribution


@then("The new Distribution is saved to database")
def created_distribution(derived_distribution, created_catalog_record):
    derived_distribution.dataset = created_catalog_record
    derived_distribution.save()

    assert derived_distribution.id is not None


@pytest.mark.stub
@then("The Dataset has persistent identifier")
def dataset_has_persistent_id(created_catalog_record):
    created_catalog_record.persistent_identifier = fake.uuid4()
    created_catalog_record.save()

    assert created_catalog_record.persistent_identifier is not None


@when("I save an draft of unpublished dataset in Qvain")
def qvain_draft_request(mock_qvain_dataset_request):
    return mock_qvain_dataset_request(status_code=201, published=False)


@then("The dataset does not have persistent identifier")
def dataset_has_no_persistent_id(created_catalog_record):
    assert created_catalog_record.persistent_identifier is None


@when("I publish new version of dataset in Qvain")
def new_dataset_version_request(mock_qvain_dataset_request):
    return mock_qvain_dataset_request(status_code=200, published=True)


@pytest.fixture
@then("Edited Dataset is saved to database as current version")
def created_new_dataset_version(created_catalog_record):
    """Should test versioning of dataset

    Current very basic versioning scheme (Research Dataset has foreign keys next, first, last, and so on..)  is
    probably going to be replaced with django-simple-history library. For some reason the foreign key relations work
    funny when foreign key points to self AND the model has OneToOne relation. Solution could be to drop the
    CatalogRecord entirely, as all of its fields can be in ResearchDataset Model.

    Args:
        created_catalog_record (): Research Dataset Object

    Returns: New instance of the Research Dataset with the modified fields

    """
    original_fields = model_to_dict(created_catalog_record)
    logger.info(original_fields)
    del original_fields["catalogrecord_ptr"]
    del original_fields["data_catalog"]
    del original_fields["language"]
    new_version = ResearchDataset(**original_fields)
    new_version.data_catalog = created_catalog_record.data_catalog
    new_version.title = {"en": "new title"}

    new_version.replaces = created_catalog_record
    new_version.save()

    # Loads RelatedObjectManager instead of foreign key object
    # assert new_version.replaces == created_catalog_record

    return new_version


@then("Previous Dataset version is still available as previous version")
def prev_dataset_exists(created_new_dataset_version, created_catalog_record):
    raise NotImplementedError


@then("Previous version is referenced in current version")
def current_dataset_has_prev_dataset_reference():
    raise NotImplementedError


@then("New Research Dataset is saved to database")
def step_impl():
    raise NotImplementedError(u"STEP: Then New Research Dataset is saved to database")
