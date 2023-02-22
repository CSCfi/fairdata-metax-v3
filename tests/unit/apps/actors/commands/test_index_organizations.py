import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.actors.models import Organization

test_settings = {
    "ORGANIZATION_DATA_FILE": "tests/unit/apps/actors/commands/testdata/test_orgs.csv",
    "ORGANIZATION_SCHEME": "http://uri.suomi.fi/codelist/fairdata/organization",
    "ORGANIZATION_BASE_URI": "http://uri.suomi.fi/codelist/fairdata/organization/code/",
}


@pytest.mark.django_db
@override_settings(**test_settings)
def test_index_organizations():
    call_command("index_organizations")
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
