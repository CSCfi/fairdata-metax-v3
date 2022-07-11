from unittest.mock import patch

import pytest
from pytest_bdd import then, scenario

from apps.core.factories import DistributionFactory


@pytest.fixture
@then("new distribution is created from the frozen files")
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


@patch("apps.core.models.CatalogRecord.creator")
@then("the user is saved as creator to the dataset")
def catalog_record_creator(published_dataset, qvain_publish_request):
    """Should be implemented at the same time as user model"""
    published_dataset.creator = qvain_publish_request.user

    assert qvain_publish_request.user is published_dataset.creator


@pytest.mark.django_db
@pytest.mark.xfail(raises=NotImplementedError)
@scenario("dataset.feature", "Publishing new dataset")
def test_dataset_publish():
    assert True
