import pytest


pytestmark = [pytest.mark.django_db]


def test_create_data_catalog_with_foreign_keys(data_catalog):
    assert data_catalog.id is not None


def test_delete_data_catalog_with_foreign_keys(data_catalog):
    publisher = data_catalog.publisher
    language = data_catalog.language
    data_catalog.delete()
    assert publisher.catalogs.filter(id=data_catalog.id).count() == 0
    # assert language.filter(catalogs__id=data_catalog_with_foreign_keys.id).count() == 0


def test_data_catalog_managed_pid_types(data_catalog):
    data_catalog.allowed_pid_types = ["URN", "DOI", "external"]
    data_catalog.save()
    assert data_catalog.managed_pid_types == ["URN", "DOI"]
