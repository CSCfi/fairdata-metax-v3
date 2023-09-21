import pytest

from apps.core.factories import DatasetActorFactory

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_create_dataset_with_foreign_keys(dataset_with_foreign_keys):
    assert dataset_with_foreign_keys.id is not None


def test_delete_dataset_with_foreign_keys(dataset_with_foreign_keys):
    data_catalog = dataset_with_foreign_keys.data_catalog
    access_rights = dataset_with_foreign_keys.access_rights
    language = dataset_with_foreign_keys.language.first()
    field_of_science = dataset_with_foreign_keys.field_of_science.first()
    theme = dataset_with_foreign_keys.theme.first()
    first = dataset_with_foreign_keys.first
    last = dataset_with_foreign_keys.last
    previous = dataset_with_foreign_keys.previous
    replaces = dataset_with_foreign_keys.replaces

    dataset_with_foreign_keys.delete()
    assert dataset_with_foreign_keys.is_removed
    assert access_rights.is_removed
    assert not access_rights.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert (
        access_rights.datasets(manager="all_objects")
        .filter(id=dataset_with_foreign_keys.id)
        .exists()
    )

    assert not data_catalog.records.filter(id=dataset_with_foreign_keys.id).exists()
    assert not language.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert not field_of_science.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert not theme.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert not first.last_version.filter(id=dataset_with_foreign_keys.id).exists()
    assert not last.first_version.filter(id=dataset_with_foreign_keys.id).exists()
    assert not previous.next.filter(id=dataset_with_foreign_keys.id).exists()
    assert not replaces.replaced_by.filter(id=dataset_with_foreign_keys.id).exists()


def test_create_dataset_actor():
    actor = DatasetActorFactory()
    assert actor.id is not None
