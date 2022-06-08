import pytest


def test_create_distribution_with_foreign_keys(distribution_with_foreign_keys):
    assert distribution_with_foreign_keys.id is not None


def test_delete_distribution_with_foreign_keys(distribution_with_foreign_keys):
    dataset_license = distribution_with_foreign_keys.license
    access_rights = distribution_with_foreign_keys.access_rights
    data_storage = distribution_with_foreign_keys.access_service
    dataset = distribution_with_foreign_keys.dataset
    distribution_with_foreign_keys.delete()
    assert (
        dataset_license.distributions.filter(id=distribution_with_foreign_keys.id).count() == 0
    )
    assert (
        access_rights.distributions.filter(id=distribution_with_foreign_keys.id).count() == 0
    )
    assert (
        data_storage.distributions.filter(id=distribution_with_foreign_keys.id).count() == 0
    )
    assert (
        dataset.distributions.filter(id=distribution_with_foreign_keys.id).count() == 0
    )