import pytest
from rest_framework.reverse import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.adapter]


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


def test_dataset_convert_from_legacy_invalid_refdata(user_client):
    dataset = {
        "research_dataset": {
            "title": {"en": "Title"},
            "field_of_science": [
                {
                    "pref_label": {"fi": "hölynpöly"},
                    "identifier": "https://example.com/doesnoexist",
                }
            ],
        },
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    assert res.status_code == 400
    data = res.json()
    assert data == [
        "FieldOfScience not found with url='https://example.com/doesnoexist']",
    ]


def test_dataset_convert_from_legacy_invalid_type(user_client):
    dataset = {
        "research_dataset": {
            "title": ["jeejee"],  # should be dict
        },
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["errors"] == {"title": ['Expected a dictionary of items but got type "list".']}


def test_dataset_convert_from_legacy_fixed_remote_resource_url(
    user_client, use_category_reference_data
):
    dataset = {
        "research_dataset": {
            "title": {"en": "Remote resource dataset"},
            "remote_resources": [
                {
                    "title": "A name given to the distribution",
                    "download_url": {
                        "identifier": "https://download.url.of.resource.com/space not allowed",
                    },
                    "use_category": {
                        "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                }
            ],
        }
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    assert res.status_code == 200
    data = res.json()
    assert "research_dataset.remote_resources[0].download_url" in data["errors"]["fixed"]


def test_dataset_convert_from_legacy_invalid_remote_resource_url(
    user_client, use_category_reference_data
):
    dataset = {
        "research_dataset": {
            "title": {"en": "Remote resource dataset"},
            "remote_resources": [
                {
                    "title": "A name given to the distribution",
                    "download_url": {
                        "identifier": "thisisnotanurl!!!",
                    },
                    "use_category": {
                        "identifier": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                    },
                }
            ],
        }
    }
    res = user_client.post(
        reverse("dataset-convert-from-legacy"), dataset, content_type="application/json"
    )
    assert res.status_code == 200
    data = res.json()
    assert "research_dataset.remote_resources[0].download_url" in data["errors"]["invalid"]
