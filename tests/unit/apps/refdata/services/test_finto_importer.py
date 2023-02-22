from os import path
from uuid import UUID

import pytest
from django.conf import settings

from apps.refdata.models import FieldOfScience, Location
from apps.refdata.services.importers import FintoImporter, FintoLocationImporter

data_sources = {
    "field_of_science": "testdata/field_of_science.ttl",
    "location": "testdata/location.ttl",
}


@pytest.fixture(scope="session")
def mock_finto_data():
    data = {}
    for key, filename in data_sources.items():
        with open(path.join(path.dirname(__file__), filename), "rb") as f:
            data[key] = f.read()
    return data


@pytest.fixture
def finto(requests_mock, mock_finto_data):
    """Mock finto service"""
    requests_mock.get(
        "https://finto-mock/field_of_science.ttl",
        content=mock_finto_data["field_of_science"],
        headers={"content-type": "text/turtle"},
    )
    requests_mock.get(
        "https://finto-mock/location.ttl",
        content=mock_finto_data["location"],
        headers={"content-type": "text/turtle"},
    )


pytestmark = pytest.mark.django_db


def test_import_finto(finto):
    importer = FintoImporter(
        model=FieldOfScience,
        source="https://finto-mock/field_of_science.ttl",
    )
    importer.load()
    values = sorted(
        FieldOfScience.all_objects.values(
            "pref_label__en",
            "url",
            "in_scheme",
            "broader__pref_label__en",
        ),
        key=lambda v: v["url"],
    )
    assert values == [
        {
            "pref_label__en": "Mathematics",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta111",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
        {
            "pref_label__en": "Statistics and probability",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta112",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
        {
            "pref_label__en": "Computer and information sciences",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta113",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
        {
            "pref_label__en": "Physical sciences",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta114",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
        {
            "pref_label__en": "Astronomy, Space science",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta115",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
        {
            "pref_label__en": "Chemical sciences",
            "url": "http://www.yso.fi/onto/okm-tieteenala/ta116",
            "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
            "broader__pref_label__en": None,
        },
    ]


def test_import_finto_location(finto):
    importer = FintoLocationImporter(
        model=Location,
        source="https://finto-mock/location.ttl",
    )
    importer.load()
    values = sorted(
        Location.all_objects.values(
            "pref_label__en",
            "url",
            "in_scheme",
            "as_wkt",
            "broader__pref_label__en",
        ),
        key=lambda v: v["url"],
    )
    assert values == [
        {
            "pref_label__en": "Pihtipudas",
            "url": "http://www.yso.fi/onto/yso/p105630",
            "in_scheme": "http://www.yso.fi/onto/yso/places",
            "as_wkt": "POINT(25.57461 63.37033)",
            "broader__pref_label__en": "Central Finland",
        },
        {
            "pref_label__en": "Kolima",
            "url": "http://www.yso.fi/onto/yso/p109185",
            "in_scheme": "http://www.yso.fi/onto/yso/places",
            "as_wkt": "POINT(25.72952 63.30445)",
            "broader__pref_label__en": "Pihtipudas",
        },
        {
            "pref_label__en": "Elämäjärvi",
            "url": "http://www.yso.fi/onto/yso/p148834",
            "in_scheme": "http://www.yso.fi/onto/yso/places",
            "as_wkt": "POINT(25.66784 63.47401)",
            "broader__pref_label__en": "Pihtipudas",
        },
        {
            "pref_label__en": "Central Finland",
            "url": "http://www.yso.fi/onto/yso/p94207",
            "in_scheme": "http://www.yso.fi/onto/yso/places",
            "as_wkt": "POINT(25.76877 62.24050)",
            "broader__pref_label__en": None,
        },
    ]
