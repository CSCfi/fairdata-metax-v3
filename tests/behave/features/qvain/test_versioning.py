import logging

import pytest
from django.forms import model_to_dict
from pytest_bdd import scenario, then, when

from apps.core.models import Dataset

logger = logging.getLogger(__name__)


@when("user publishes new version of dataset in Qvain")
def new_dataset_version_request(mock_qvain_dataset_with_files_request):
    yield mock_qvain_dataset_with_files_request(status_code=200, published=True)
    raise NotImplementedError


@pytest.fixture
@when("edited dataset is saved as a new version of the dataset")
def created_new_dataset_version(published_dataset):
    """Tests versioning in dataset

    Current very basic versioning scheme (Research Dataset has foreign keys next, first, last, and so on..)  is
    probably going to be replaced with django-simple-history library.

    Args:
        published_dataset (): Research Dataset Object

    Returns: New instance of the Research Dataset with the modified fields

    """
    raise NotImplementedError
    original_fields = model_to_dict(published_dataset)
    logger.info(original_fields)
    del original_fields["data_catalog"]
    del original_fields["language"]
    del original_fields["contract"]
    del original_fields["system_creator"]
    del original_fields["creator"]
    new_version = Dataset(**original_fields)

    new_version = Dataset(**original_fields)
    new_version.data_catalog = published_dataset.data_catalog
    new_version.title = {"en": "new title"}

    new_version.replaces = published_dataset
    new_version.previous = published_dataset
    new_version.save()
    published_dataset.save()

    return new_version


@then("previous dataset version is still available as previous version")
def prev_dataset_exists(created_new_dataset_version, published_dataset):
    assert created_new_dataset_version.replaces == published_dataset
    assert created_new_dataset_version.previous == published_dataset


@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Publishing new version from dataset")
@pytest.mark.django_db
def test_dataset_new_version(created_new_dataset_version, published_dataset):
    assert (
        created_new_dataset_version.persistent_identifier
        == published_dataset.persistent_identifier
    )
