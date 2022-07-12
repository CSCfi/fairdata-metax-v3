from unittest.mock import patch

import pytest
from pytest_bdd import then, scenario

from apps.core.factories import DistributionFactory
from apps.core.models import Distribution


@pytest.fixture
@then("new distribution is created from the frozen files")
def derived_distribution(
    frozen_distribution, qvain_publish_request, published_dataset
) -> Distribution:
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
    derived_distribution.dataset = published_dataset
    derived_distribution.save()
    return derived_distribution


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
