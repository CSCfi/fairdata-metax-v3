import pytest


def test_create_data_catalog_with_foreign_keys(data_catalog_with_foreign_keys):
    assert data_catalog_with_foreign_keys.id is not None


def test_delete_data_catalog_with_foreign_keys(data_catalog_with_foreign_keys):
    access_rights = data_catalog_with_foreign_keys.access_rights
    publisher = data_catalog_with_foreign_keys.publisher
    language = data_catalog_with_foreign_keys.language
    data_catalog_with_foreign_keys.delete()
    assert (
        access_rights.catalogs.filter(id=data_catalog_with_foreign_keys.id).count() == 0
    )
    assert publisher.catalogs.filter(id=data_catalog_with_foreign_keys.id).count() == 0
    assert language.filter(id=data_catalog_with_foreign_keys.id).count() == 0
