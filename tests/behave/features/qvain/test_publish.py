from unittest.mock import Mock, patch

import pytest
from pytest_bdd import scenario, then, when


@pytest.fixture
@when("the user is saved as creator to the dataset")
def catalog_record_creator(published_dataset, qvain_publish_request, qvain_user):
    """Ensure dataset has the right creator

    Args:
        published_dataset ():
        qvain_publish_request ():

    Returns:

    """
    published_dataset.system_creator = qvain_user
    yield published_dataset
    raise NotImplementedError


@then("dataset is published")
def dataset_is_published(published_dataset, ida_data_catalog):
    """

    Args:
        published_dataset (Dataset): Research Dataset to be published

    """
    assert published_dataset.data_catalog == ida_data_catalog
    assert published_dataset.issued is not None


@then("published dataset exists with persistent identifier")
def published_dataset(published_dataset, qvain_publish_request):
    """

    Args:
        published_dataset (Dataset): Research Dataset to be published

    """
    assert published_dataset.persistent_identifier is not None


@then("the dataset has a creator")
def dataset_has_creator(catalog_record_creator, qvain_publish_request, published_dataset):
    """

    Args:
        catalog_record_creator ():
        qvain_publish_request (): publish API-request
        published_dataset (Dataset):

    Returns:

    """
    assert qvain_publish_request.user is published_dataset.system_creator


@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Publishing new dataset")
def test_dataset_publish(published_dataset, ida_data_catalog):
    assert published_dataset.data_catalog == ida_data_catalog
    assert published_dataset.issued is not None
