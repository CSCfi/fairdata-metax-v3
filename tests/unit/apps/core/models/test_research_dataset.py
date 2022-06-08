import pytest


def test_create_research_dataset_with_foreign_keys(research_dataset_with_foreign_keys):
    assert research_dataset_with_foreign_keys.id is not None


def test_delete_research_dataset_with_foreign_keys(research_dataset_with_foreign_keys):
    data_catalog = research_dataset_with_foreign_keys.data_catalog
    access_right = research_dataset_with_foreign_keys.access_right
    language = research_dataset_with_foreign_keys.language
    first = research_dataset_with_foreign_keys.first
    last = research_dataset_with_foreign_keys.last
    previous = research_dataset_with_foreign_keys.previous
    replaces = research_dataset_with_foreign_keys.replaces
    research_dataset_with_foreign_keys.delete()
    assert (
        data_catalog.records.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )
    assert (
        access_right.research_datasets.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )
    # assert (
    #     language.research_datasets.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    # )
    assert (
        first.last_version.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )
    assert (
        last.first_version.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )
    assert (
        previous.next.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )
    assert (
        replaces.replaced_by.filter(id=research_dataset_with_foreign_keys.id).count() == 0
    )