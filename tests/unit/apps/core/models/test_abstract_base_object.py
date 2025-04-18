import pytest

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.parametrize(
        "model",
        ["dataset_publisher", "access_rights", "file", "contract"],
    ),
]


def test_create_base_model(model, abstract_base_object_factory):
    """

    Args:
        model (): Django Model with direct inheritance from AbstractBaseModel
        abstract_base_object_factory ():

    Returns:

    """
    obj = abstract_base_object_factory(model)
    assert obj.id is not None


def test_hard_delete_base_model(model, abstract_base_object_factory):
    obj = abstract_base_object_factory(model)
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0


def test_soft_delete_base_model(model, abstract_base_object_factory):
    obj = abstract_base_object_factory(model)
    obj.delete()
    assert obj.removed is not None
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1
