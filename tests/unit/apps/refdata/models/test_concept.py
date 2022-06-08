from uuid import UUID
from django.db import IntegrityError
import pytest

from apps.refdata.models import FieldOfScience

pytestmark = pytest.mark.parametrize(
    "model",
    [
        FieldOfScience,
    ],
)


fields = dict(
    url="https://example.com/test",
    in_scheme="https://example.com",
    pref_label={"en": "Field"},
    is_reference_data=False,
)


def test_create_duplicate_reference_data_url(model):
    model.objects.create(**{**fields, "is_reference_data": True})
    with pytest.raises(IntegrityError):
        model.objects.create(**{**fields, "is_reference_data": True})


def test_create_reference_data_without_scheme(model):
    with pytest.raises(IntegrityError):
        model.objects.create(**{**fields, "in_scheme": "", "is_reference_data": True})


def test_create_concept_without_scheme(model):
    model.objects.create(**{**fields, "in_scheme": ""})


def test_create_concept_without_url(model):
    with pytest.raises(IntegrityError):
        model.objects.create(**{**fields, "url": ""})


def test_hard_delete_concept(model):
    obj = model.objects.create(**fields)
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0


def test_soft_delete_concept(model):
    obj = model.objects.create(**fields)
    obj.delete()
    assert obj.is_removed is True
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1


@pytest.mark.django_db
def test_serialize_concept(model):
    obj = model.objects.create(**{**fields, "id": UUID(int=0)})
    serialized_data = model.get_serializer()(obj).data
    assert serialized_data == {
        "id": "00000000-0000-0000-0000-000000000000",
        "url": "https://example.com/test",
        "in_scheme": "https://example.com",
        "pref_label": {"en": "Field"},
        "broader": [],
        "narrower": [],
    }
