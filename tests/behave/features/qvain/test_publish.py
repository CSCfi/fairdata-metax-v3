from unittest.mock import patch, Mock

import pytest
from pytest_bdd import then, scenario, when


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


@then("published dataset exists with persistent identifier and new distribution")
def published_dataset_with_distribution(
    published_dataset, derived_distribution, frozen_distribution, qvain_publish_request
):
    """

    Args:
        published_dataset (ResearchDataset): Research Dataset to be published
        derived_distribution (): User chosen files to include to distribution
        frozen_distribution (): Original Distribution from the freeze action on IDA
        qvain_publish_request (): Publish API-request

    """
    assert published_dataset.persistent_identifier is not None
    assert (
        frozen_distribution.files.intersection(qvain_publish_request.files).count()
        == derived_distribution.files.count()
    )


@then("the dataset has a creator")
def dataset_has_creator(
    catalog_record_creator, qvain_publish_request, published_dataset
):
    """

    Args:
        catalog_record_creator ():
        qvain_publish_request (): publish API-request
        published_dataset (ResearchDataset):

    Returns:

    """
    assert qvain_publish_request.user is published_dataset.system_creator


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Publishing new dataset")
def test_dataset_publish(derived_distribution, published_dataset, ida_data_catalog):
    assert published_dataset.data_catalog == ida_data_catalog
    assert derived_distribution.dataset == published_dataset
    assert published_dataset.release_date is not None
