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

    dataset_with_foreign_keys.delete()
    assert dataset_with_foreign_keys.removed
    assert access_rights.removed
    assert not access_rights.dataset.filter(id=dataset_with_foreign_keys.id).exists()
    assert (
        access_rights.dataset(manager="all_objects")
        .filter(id=dataset_with_foreign_keys.id)
        .exists()
    )

    assert not data_catalog.records.filter(id=dataset_with_foreign_keys.id).exists()
    assert not language.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert not field_of_science.datasets.filter(id=dataset_with_foreign_keys.id).exists()
    assert not theme.datasets.filter(id=dataset_with_foreign_keys.id).exists()


def test_create_dataset_actor():
    actor = DatasetActorFactory()
    assert actor.id is not None
