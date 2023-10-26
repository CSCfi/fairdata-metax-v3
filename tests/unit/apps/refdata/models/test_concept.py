from uuid import UUID

import pytest
from django.db import IntegrityError

from apps.refdata.models import FieldOfScience, Language, Location, Theme

pytestmark = pytest.mark.parametrize(
    "model",
    [
        FieldOfScience,
        Language,
        Location,
        Theme,
    ],
)

extra_field_values = {"as_wkt": None}


fields = dict(
    url="https://example.com/test",
    in_scheme="https://example.com",
    pref_label={"en": "Field"},
)


def test_create_duplicate_reference_data_url(model):
    model.all_objects.create(**{**fields})
    with pytest.raises(IntegrityError):
        model.all_objects.create(**{**fields})


def test_create_reference_data_without_scheme(model):
    with pytest.raises(IntegrityError):
        model.all_objects.create(**{**fields, "in_scheme": ""})


def test_create_concept_without_url(model):
    with pytest.raises(IntegrityError):
        model.all_objects.create(**{**fields, "url": ""})


def test_hard_delete_concept(model):
    obj = model.all_objects.create(**fields)
    obj.delete(soft=False)
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 0


def test_soft_delete_concept(model):
    obj = model.all_objects.create(**fields)
    obj.delete()
    assert obj.removed is not None
    assert obj.__class__.all_objects.filter(id=obj.id).count() == 1


@pytest.mark.django_db
def test_serialize_concept(model):
    obj = model.all_objects.create(**{**fields, "id": UUID(int=0)})
    serialized_data = model.get_serializer_class()(obj).data
    assert serialized_data == {
        "id": "00000000-0000-0000-0000-000000000000",
        "url": "https://example.com/test",
        "in_scheme": "https://example.com",
        "pref_label": {"en": "Field"},
        "broader": [],
        "narrower": [],
        **{
            field: extra_field_values[field]
            for field in getattr(model, "serializer_extra_fields", [])
        },
    }
