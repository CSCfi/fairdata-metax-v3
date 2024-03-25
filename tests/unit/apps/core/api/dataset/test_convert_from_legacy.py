import pytest
from rest_framework.reverse import reverse

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.dataset, pytest.mark.legacy]


def test_dataset_convert_from_legacy_minimal(user_client):
    dataset = {
        "research_dataset": {
            "title": {"en": "Title"},
        },
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    data = res.json()
    assert data == {
        "title": {"en": "Title"},
    }


def test_dataset_convert_from_legacy(user_client):
    dataset = {
        "research_dataset": {
            "description": {"en": "Description"},
            "rights_holder": [
                {
                    "@type": "Person",
                    "name": "teppo",
                    "member_of": {"@type": "Organization", "name": {"en": "teppo org"}},
                }
            ],
            "creator": [{"@type": "Person", "name": "mauno"}],
            "publisher": {"@type": "Person", "name": "mauno"},
        },
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    data = res.json()
    assert data == {
        "description": {"en": "Description"},
        "actors": [
            {"person": {"name": "mauno"}, "roles": ["creator", "publisher"]},
            {
                "person": {"name": "teppo"},
                "organization": {"pref_label": {"en": "teppo org"}},
                "roles": ["rights_holder"],
            },
        ],
        "errors": {"title": ["This field is required."]},
    }
