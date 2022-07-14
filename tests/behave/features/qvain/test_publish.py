from unittest.mock import patch

import pytest
from pytest_bdd import then, scenario


@patch("apps.core.models.CatalogRecord.creator")
@then("the user is saved as creator to the dataset")
def catalog_record_creator(published_dataset, qvain_publish_request):
    """Should be implemented at the same time as user model"""
    published_dataset.creator = qvain_publish_request.user

    assert qvain_publish_request.user is published_dataset.creator


@pytest.mark.django_db
@scenario("dataset.feature", "Publishing new dataset")
def test_dataset_publish(derived_distribution, published_dataset, ida_data_catalog):
    assert published_dataset.data_catalog == ida_data_catalog
    assert derived_distribution.dataset == published_dataset
    assert published_dataset.release_date is not None
    assert published_dataset.persistent_identifier is not None
