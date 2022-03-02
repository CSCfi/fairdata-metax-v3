import pytest


def test_create_language(dataset_language):
    identifier = dataset_language.identifier
    dataset_language.save()
    assert dataset_language.identifier == identifier


def test_create_homepage(catalog_homepage):
    identifier = catalog_homepage.identifier
    catalog_homepage.save()
    assert catalog_homepage.identifier == identifier


def test_create_publisher(catalog_homepage, dataset_publisher):
    catalog_homepage.save()
    dataset_publisher.save()
    dataset_publisher.homepage.add(catalog_homepage)
    assert dataset_publisher.id is not None
    assert dataset_publisher.homepage.count() != 0


def test_create_license(dataset_license):
    identifier = dataset_license.identifier
    dataset_license.save()
    assert dataset_license.identifier == identifier


def test_create_access_rights(access_rights, access_type, dataset_license):
    access_type.save()
    dataset_license.save()
    access_rights.license = dataset_license
    access_rights.access_type = access_type
    access_rights.save()
    assert access_rights.id is not None


def test_create_data_catalog(
    dataset_language, dataset_publisher, access_rights, data_catalog
):
    identifier = data_catalog.identifier
    dataset_language.save()
    dataset_publisher.save()
    access_rights.save()
    data_catalog.access_rights = access_rights
    data_catalog.publisher = dataset_publisher
    data_catalog.language.add(dataset_language)
    data_catalog.save()
    assert data_catalog.identifier == identifier
