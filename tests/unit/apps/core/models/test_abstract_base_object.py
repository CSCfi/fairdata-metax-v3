import pytest

pytestmark = pytest.mark.parametrize(
    "model", ["dataset_publisher", "access_rights", "catalog_record", "data_storage", "file", "contract"]
)


def test_create_base_model(model, abstract_base_object_factory):
    obj = abstract_base_object_factory(model)
    assert obj.id is not None


def test_hard_delete_base_model(model, abstract_base_object_factory):
    obj = abstract_base_object_factory(model)
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0


def test_soft_delete_base_model(model, abstract_base_object_factory):
    obj = abstract_base_object_factory(model)
    obj.delete()
    assert obj.is_removed is True
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1
