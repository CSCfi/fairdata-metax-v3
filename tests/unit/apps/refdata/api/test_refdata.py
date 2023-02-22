from uuid import UUID

import inflection
import pytest

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

common_fields = {"in_scheme": "https://example.com", "is_reference_data": True}
extra_field_values = {"as_wkt": ""}


def get_model_url(model):
    return f"/reference_data/{inflection.underscore(model.__name__)}"


@pytest.mark.django_db
def test_get_concept(client, model):
    model.all_objects.create(
        url="https://example.com/test",
        id=UUID(int=0),
        pref_label={"en": "Field"},
        **common_fields,
    )
    url = get_model_url(model)
    resp = client.get(url)
    assert resp.data["results"] == [
        {
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
    ]


@pytest.fixture
def assert_query_results(client, model):
    model.all_objects.create(
        url="https://example.com/test_x",
        id=UUID(int=0),
        pref_label={"en": "Item x"},
        **common_fields,
    )
    model.all_objects.create(
        url="https://example.com/test_y",
        id=UUID(int=1),
        pref_label={"en": "Item y"},
        **common_fields,
    )

    def do_query(query, expected_labels):
        url = get_model_url(model)
        resp = client.get(url, query)
        assert [
            obj["pref_label"]["en"] for obj in resp.data["results"]
        ] == expected_labels

    return do_query


@pytest.mark.django_db
def test_filter_concept_by_pref_label(assert_query_results):
    assert_query_results({"pref_label": "Item"}, ["Item x", "Item y"])
    assert_query_results({"pref_label": "Item x"}, ["Item x"])
    assert_query_results({"pref_label": "Item y"}, ["Item y"])
    assert_query_results({"pref_label": "Item z"}, [])


@pytest.mark.django_db
def test_filter_concept_by_url(assert_query_results):
    assert_query_results({"url": "https://example.com/test"}, ["Item x", "Item y"])
    assert_query_results({"url": "https://example.com/test_x"}, ["Item x"])
    assert_query_results({"url": "https://example.com/test_y"}, ["Item y"])
    assert_query_results({"url": "https://example.com/test_z"}, [])


@pytest.mark.django_db
def test_order_concept(assert_query_results):
    assert_query_results({"ordering": "created"}, ["Item x", "Item y"])
    assert_query_results({"ordering": "-created"}, ["Item y", "Item x"])
    assert_query_results({"ordering": "url"}, ["Item x", "Item y"])
    assert_query_results({"ordering": "-url"}, ["Item y", "Item x"])
