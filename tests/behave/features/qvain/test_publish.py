from unittest.mock import patch, Mock

import pytest
from pytest_bdd import then, scenario, when


@pytest.fixture
@when("the user is saved as creator to the dataset")
def catalog_record_creator(published_dataset, qvain_publish_request):
    """

    Args:
        published_dataset ():
        qvain_publish_request ():

    Returns:

    """
    published_dataset.creator = Mock()
    published_dataset.creator = qvain_publish_request.user
    return published_dataset


@then("published dataset exists with persistent identifier and new distribution")
def published_dataset_with_distribution(
    published_dataset, derived_distribution, frozen_distribution, qvain_publish_request
):
    """

    Args:
        published_dataset ():
        derived_distribution ():
        frozen_distribution ():
        qvain_publish_request ():

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
        qvain_publish_request ():
        published_dataset ():

    Returns:

    """
    assert qvain_publish_request.user is published_dataset.creator


@pytest.mark.django_db
@scenario("dataset.feature", "Publishing new dataset")
def test_dataset_publish(derived_distribution, published_dataset, ida_data_catalog):
    assert published_dataset.data_catalog == ida_data_catalog
    assert derived_distribution.dataset == published_dataset
    assert published_dataset.release_date is not None
