import pytest

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.parametrize(
        "dataset_property",
        [
            "catalog_homepage",
            "data_catalog",
        ],
    ),
]


@pytest.mark.parametrize(
    "dataset_ref_property",
    ["catalog_homepage"],
)
def test_create_dataset_ref_property(
    dataset_property, dataset_ref_property, dataset_property_object_factory
):
    obj = dataset_property_object_factory(dataset_ref_property)
    identifier = obj.url
    assert obj.url == identifier


@pytest.mark.parametrize("dataset_base_property", ["data_catalog"])
def test_create_dataset_property(
    dataset_property, dataset_base_property, dataset_property_object_factory
):
    obj = dataset_property_object_factory(dataset_base_property)
    identifier = obj.id
    assert obj.id == identifier


def test_soft_delete_dataset_property(dataset_property, dataset_property_object_factory):
    obj = dataset_property_object_factory(dataset_property)
    obj.delete()
    assert obj.removed is not None
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1


def test_hard_delete_dataset_property(dataset_property, dataset_property_object_factory):
    obj = dataset_property_object_factory(dataset_property)
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0
    assert obj.__class__.available_objects.filter(id=obj.id).count() == 0
