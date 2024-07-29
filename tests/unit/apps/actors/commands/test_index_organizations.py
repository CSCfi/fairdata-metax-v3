import os
from urllib.parse import quote

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.actors.models import Organization

test_settings = {
    "ORGANIZATION_DATA_FILE": "tests/unit/apps/actors/commands/testdata/test_orgs.csv",
    "ORGANIZATION_SCHEME": "http://uri.suomi.fi/codelist/fairdata/organization",
    "ORGANIZATION_BASE_URI": "http://uri.suomi.fi/codelist/fairdata/organization/code/",
    "ORGANIZATION_FETCH_API_URL": None,
}

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/testdata/"


@pytest.mark.django_db
@override_settings(**test_settings)
def test_index_organizations_from_file():
    call_command("index_organizations", "--cached")
    orgs = Organization.available_objects.values(
        "pref_label__en", "parent__pref_label__en", "code", "url", "in_scheme"
    )

    expected_orgs = [
        {
            "pref_label__en": "Aalto University",
            "parent__pref_label__en": None,
            "code": "10076",
        },
        {
            "pref_label__en": "Geological Survey of Finland",
            "parent__pref_label__en": None,
            "code": "5040011",
        },
        {
            "pref_label__en": "LUT University",
            "parent__pref_label__en": None,
            "code": "01914",
        },
        {
            "pref_label__en": "ARTS Infra",
            "parent__pref_label__en": "Aalto University",
            "code": "10076-A855",
        },
        {
            "pref_label__en": "Aalto Common Items",
            "parent__pref_label__en": "Aalto University",
            "code": "10076-U920",
        },
        {
            "pref_label__en": "Aalto Nanofab",
            "parent__pref_label__en": "Aalto University",
            "code": "10076-T409",
        },
        {
            "pref_label__en": "Aalto Studios",
            "parent__pref_label__en": "Aalto University",
            "code": "10076-A850",
        },
        {
            "pref_label__en": "Alueellinen geotieto ALG",
            "parent__pref_label__en": "Geological Survey of Finland",
            "code": "5040011-504030014",
        },
    ]
    for org in expected_orgs:
        org["in_scheme"] = test_settings["ORGANIZATION_SCHEME"]
        org["url"] = f"{test_settings['ORGANIZATION_BASE_URI']}{org['code']}"

    assert list(orgs) == expected_orgs


@pytest.mark.django_db
@override_settings(
    **{
        **test_settings,
        "ORGANIZATION_DATA_FILE": None,
        "ORGANIZATION_FETCH_API_URL": "https://referenceorganizations.com/_search",
    }
)
def test_index_organizations_from_api(requests_mock):
    with open(f"{test_data_path}test_orgs.json", "rb") as datafile:
        requests_mock.get(
            "https://referenceorganizations.com/_search",
            content=datafile.read(),
        )

    call_command("index_organizations")
    orgs = Organization.available_objects.values(
        "pref_label__en", "parent__pref_label__en", "code", "url", "in_scheme"
    )

    expected_orgs = [
        {
            "pref_label__en": "Diaconia University of Applied Sciences",
            "parent__pref_label__en": None,
            "code": "02623",
        },
        {
            "pref_label__en": "Innovaatiot ja kumppanuudet tulosalue",
            "parent__pref_label__en": "Diaconia University of Applied Sciences",
            "code": "02623-100",
        },
        {
            "pref_label__en": "Sub org with space",
            "parent__pref_label__en": "Diaconia University of Applied Sciences",
            "code": "02623-105 123",
        },
    ]
    for org in expected_orgs:
        org["in_scheme"] = test_settings["ORGANIZATION_SCHEME"]
        org["url"] = f"{test_settings['ORGANIZATION_BASE_URI']}{quote(org['code'])}"

    assert list(orgs) == expected_orgs


@pytest.mark.django_db
@override_settings(**test_settings)
def test_index_organizations_deprecation():
    """Reference data organizations removed from source data should be deprecated."""
    dep1 = Organization.objects.create(
        pref_label={"en": "This will be deprecated"},
        url=f"{test_settings['ORGANIZATION_BASE_URI']}deprecateme",
        in_scheme=test_settings["ORGANIZATION_SCHEME"],
        is_reference_data=True,
    )
    dep2 = Organization.objects.create(
        pref_label={"en": "This too"},
        url=f"{test_settings['ORGANIZATION_BASE_URI']}deprecatemetoo",
        in_scheme=test_settings["ORGANIZATION_SCHEME"],
        is_reference_data=True,
    )
    # Deprecated entry should be undeprecated when it is found in the data source
    undep = Organization.objects.create(
        url=f"{test_settings['ORGANIZATION_BASE_URI']}10076",
        deprecated="2022-01-02T11:22:33Z",
        pref_label={"en": "Aalto"},
        in_scheme=test_settings["ORGANIZATION_SCHEME"],
        is_reference_data=True,
    )

    call_command("index_organizations", "--cached")
    deprecated_orgs = Organization.available_objects.filter(deprecated__isnull=False)
    assert set(deprecated_orgs) == {dep1, dep2}

    undep.refresh_from_db()
    assert undep.deprecated is None
