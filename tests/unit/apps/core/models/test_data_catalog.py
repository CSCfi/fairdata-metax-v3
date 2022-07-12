import pytest


def test_create_data_catalog_with_foreign_keys(data_catalog):
    assert data_catalog.id is not None


def test_delete_data_catalog_with_foreign_keys(data_catalog):
    access_rights = data_catalog.access_rights
    publisher = data_catalog.publisher
    language = data_catalog.language
    data_catalog.delete()
    assert access_rights.catalogs.filter(id=data_catalog.id).count() == 0
    assert publisher.catalogs.filter(id=data_catalog.id).count() == 0
    # assert language.filter(catalogs__id=data_catalog_with_foreign_keys.id).count() == 0
