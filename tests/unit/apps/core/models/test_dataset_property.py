import pytest

pytestmark = pytest.mark.parametrize(
    "dataset_property",
    [
        "dataset_language",
        "catalog_homepage",
        "dataset_license",
        "access_type",
        "data_catalog",
        "distribution",
    ],
)


def test_create_dataset_property(dataset_property, dataset_property_object_factory):
    obj = dataset_property_object_factory(dataset_property)
    identifier = obj.id
    obj.save()
    assert obj.id == identifier


def test_soft_delete_dataset_property(
    dataset_property, dataset_property_object_factory
):
    obj = dataset_property_object_factory(dataset_property)
    obj.save()
    obj.delete()
    assert obj.is_removed is True
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1


def test_hard_delete_dataset_property(
    dataset_property, dataset_property_object_factory
):
    obj = dataset_property_object_factory(dataset_property)
    obj.save()
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0
    assert obj.__class__.available_objects.filter(id=obj.id).count() == 0
