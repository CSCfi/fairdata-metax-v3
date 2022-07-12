import pytest


def test_create_distribution_with_foreign_keys(distribution):
    assert distribution.id is not None


def test_delete_distribution_with_foreign_keys(distribution):
    dataset_license = distribution.license
    access_rights = distribution.access_rights
    data_storage = distribution.access_service
    dataset = distribution.dataset
    distribution.delete()
    assert dataset_license.distributions.filter(id=distribution.id).count() == 0
    assert access_rights.distributions.filter(id=distribution.id).count() == 0
    assert data_storage.distributions.filter(id=distribution.id).count() == 0
    assert dataset.distributions.filter(id=distribution.id).count() == 0
