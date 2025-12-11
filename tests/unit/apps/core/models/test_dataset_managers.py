import pytest

from apps.core import factories
from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db]


def test_filter_rems_datasets():
    """Test rems_datasets method of Dataset managers."""
    # Check all Dataset managers have rems_datasets
    assert hasattr(Dataset.available_objects, "rems_datasets")
    assert hasattr(Dataset.objects, "rems_datasets")
    assert hasattr(Dataset.all_objects, "rems_datasets")

    # Check rems datasets returns correct datasets
    no_rems = factories.PublishedDatasetFactory()
    yes_rems = factories.REMSDatasetFactory()
    missing_organization = factories.REMSDatasetFactory(metadata_owner__admin_organization=None)

    datasets = Dataset.objects.order_by("created")
    assert set(datasets.rems_datasets()) == {yes_rems}
    assert set(datasets.rems_datasets(exclude=True)) == {
        no_rems,
        missing_organization,
    }

    # Check that adding missing admin_organization fixes dataset so it is listed as REMS dataset
    missing_organization.metadata_owner = yes_rems.metadata_owner
    missing_organization.save()
    assert set(datasets.rems_datasets()) == {yes_rems, missing_organization}
    assert set(datasets.rems_datasets(exclude=True)) == {no_rems}
