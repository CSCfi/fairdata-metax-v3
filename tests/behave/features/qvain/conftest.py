from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from pytest_bdd import scenario, given, when, then

from apps.core.factories import FileFactory, CatalogRecordFactory, DistributionFactory
from apps.core.models import CatalogRecord


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


@pytest.mark.stub
@when("I publish a new dataset in Qvain")
def qvain_publish_request():
    """Makes API-Request to Dataset API with Dataset information

    Returns: API Request Response for Qvain

    """
    request = MagicMock()
    request.status_code = 201
    return request


@pytest.fixture
@then("New Catalog Record is saved to database")
def created_catalog_record(ida_data_catalog) -> CatalogRecord:
    """CatalogRecord is distinct object, separate from Dataset

    TODO: CatalogRecord should be generated in the qvain_publish_request step instead of using CatalogRecordFactory
    TODO: This step should do an assert instead of being a fixture

    Args:
        ida_data_catalog (): IDA DataCatalog

    Returns: CatalogRecord object to use with Dataset object

    """
    return CatalogRecordFactory(data_catalog=ida_data_catalog)


@then("The User is saved as creator to the Catalog Record")
def catalog_record_creator():
    raise NotImplementedError


@then("New Dataset is saved to database")
def created_dataset():
    raise NotImplementedError


@then("New Distribution is derived from frozen files Distribution")
def derived_distribution(frozen_distribution):
    """Frozen distribution is generated when files are frozen in IDA

    If the dataset files are different from frozen distribution, new distribution should be created.
    This new distribution would reference the frozen distribution. This is possible if Distribution object has
    ForeignKey to self.

    It is currently unclear if new distribution should be created for every freeze operation.
    """
    raise NotImplementedError


@then("The new Distribution is saved to database")
def created_distribution():
    raise NotImplementedError


@then("The Dataset has persistent identifier")
def dataset_has_persistent_id():
    raise NotImplementedError


@when("I save an draft of unpublished dataset in Qvain")
def qvain_draft_request():
    raise NotImplementedError


@then("The dataset does not have persistent identifier")
def dataset_has_no_persistent_id():
    raise NotImplementedError


@when("I publish new version of dataset in Qvain")
def new_dataset_version_request():
    raise NotImplementedError


@then("Edited Dataset is saved to database as current version")
def created_new_dataset_version():
    raise NotImplementedError


@then("Previous Dataset version is still available as previous version")
def prev_dataset_exists():
    raise NotImplementedError


@then("Previous version is referenced in current version")
def current_dataset_has_prev_dataset_reference():
    raise NotImplementedError
