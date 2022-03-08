import pytest


def test_create_publisher_with_webpage(catalog_homepage, dataset_publisher):
    catalog_homepage.save()
    dataset_publisher.save()
    dataset_publisher.homepage.add(catalog_homepage)
    assert dataset_publisher.id is not None
    assert dataset_publisher.homepage.count() != 0
    assert dataset_publisher.homepage.get(id=catalog_homepage.id) == catalog_homepage


def test_delete_with_web_page(dataset_publisher, catalog_homepage):
    dataset_publisher.save()
    catalog_homepage.save()
    dataset_publisher.homepage.add(catalog_homepage)
    dataset_publisher.delete()
    assert catalog_homepage.publishers.filter(id=dataset_publisher.id).count() == 0
