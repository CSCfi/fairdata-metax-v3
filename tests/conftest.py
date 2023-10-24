# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for metax_service.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

import django
import factory.random
import pytest
from django.conf import settings
from rest_framework.test import APIClient, RequestsClient

from apps.core import factories
from apps.core.models.data_catalog import DataCatalog


@pytest.fixture(scope="session", autouse=True)
def faker_session_locale():
    return ["en_US"]


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return settings.FACTORY_BOY_RANDOM_SEED


def pytest_collection_modifyitems(items):
    """Pytest provided hook function

    Pytest hook docs: https://docs.pytest.org/en/latest/how-to/writing_hook_functions.html
    """
    django.setup()
    factory.random.reseed_random(settings.FACTORY_BOY_RANDOM_SEED)
    for item in items:
        if "create" in item.nodeid or "delete" in item.nodeid:
            # adds django_db marker on any test with 'create' or 'delete' on its name
            item.add_marker(pytest.mark.django_db)
        if "behave" in item.nodeid:
            item.add_marker(pytest.mark.behave)
            item.add_marker(pytest.mark.django_db)
        if "unit" in item.nodeid:
            item.add_marker("unit")
            item.add_marker(pytest.mark.django_db)


@pytest.fixture
def data_catalog() -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-ida"
    title = {
        "en": "Fairdata IDA datasets",
        "fi": "Fairdata IDA-aineistot",
        "sv": "Fairdata forskningsdata",
    }
    return factories.DataCatalogFactory(id=identifier, title=title, dataset_versioning_enabled=True)


@pytest.mark.django_db
@pytest.fixture
def access_type_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/access_type",
    }
    factories.AccessTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open",
        pref_label={"fi": "Avoin", "en": "Open"},
        same_as=["http://publications.europa.eu/resource/authority/access-right/PUBLIC"],
        **common_args,
    )
    factories.AccessTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/login",
        pref_label={
            "fi": "Vaatii kirjautumisen Fairdata-palvelussa",
            "en": "Requires login in Fairdata service",
        },
        same_as=["http://publications.europa.eu/resource/authority/access-right/RESTRICTED"],
        **common_args,
    )
    factories.AccessTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/permit",
        pref_label={
            "fi": "Vaatii luvan hakemista Fairdata-palvelussa",
            "en": "Requires applying permission in Fairdata service",
        },
        same_as=["http://publications.europa.eu/resource/authority/access-right/RESTRICTED"],
        **common_args,
    )
    factories.AccessTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/restricted",
        pref_label={"fi": "Saatavuutta rajoitettu", "en": "Restricted use"},
        same_as=["http://publications.europa.eu/resource/authority/access-right/RESTRICTED"],
        **common_args,
    )
    factories.AccessTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/access_type/code/embargo",
        pref_label={"fi": "Embargo", "en": "Embargo"},
        same_as=["http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"],
        **common_args,
    )


@pytest.fixture
def field_of_science_reference_data():
    common_args = {
        "in_scheme": "http://www.yso.fi/onto/okm-tieteenala/conceptscheme",
    }
    factories.FieldOfScienceFactory(
        url="http://www.yso.fi/onto/okm-tieteenala/ta113",
        pref_label={
            "en": "Computer and information sciences",
            "fi": "Tietojenkäsittely ja informaatiotieteet",
            "sv": "Data- och informationsvetenskap",
        },
        **common_args,
    )
    field_a = factories.FieldOfScienceFactory(
        url="http://www.yso.fi/onto/okm-tieteenala/ta111",
        pref_label={"en": "Mathematics", "fi": "Matematiikka", "sv": "Matematik"},
        **common_args,
    )
    field_b = factories.FieldOfScienceFactory(
        url="http://www.yso.fi/onto/okm-tieteenala/ta112",
        pref_label={
            "en": "Statistics and probability",
            "fi": "Tilastotiede",
            "sv": "Statistik",
        },
        **common_args,
    )
    broader_field = factories.FieldOfScienceFactory(
        url="http://www.yso.fi/onto/okm-tieteenala/ta1",
        pref_label={
            "en": "Natural sciences",
            "fi": "LUONNONTIETEET",
            "sv": "Naturvetenskaper",
        },
        **common_args,
    )
    broader_field.narrower.set([field_a, field_b])


@pytest.fixture
def theme_reference_data():
    common_args = {
        "in_scheme": "http://www.yso.fi/onto/koko/",
    }
    factories.ThemeFactory(
        url="http://www.yso.fi/onto/koko/p1",
        pref_label={
            "en": "data systems designers",
            "fi": "atk-suunnittelijat",
            "sv": "adb-planerare",
        },
        **common_args,
    )
    keyword = factories.ThemeFactory(
        url="http://www.yso.fi/onto/koko/p10",
        pref_label={
            "en": "test subjects (persons)",
            "fi": "koehenkilöt",
            "sv": "försökspersoner",
        },
        **common_args,
    )
    broader_keyword = factories.ThemeFactory(
        url="http://www.yso.fi/onto/koko/p37018",
        pref_label={
            "en": "role related to action",
            "fi": "toimintaan liittyvä rooli",
            "sv": "roll relaterad till verksamhet",
        },
        **common_args,
    )
    keyword.broader.set([broader_keyword])
    factories.ThemeFactory(
        url="http://www.yso.fi/onto/koko/p36817",
        pref_label={
            "en": "testing",
            "fi": "testaus",
            "sv": "testning",
            "sme": "testen",
        },
        **common_args,
    )


@pytest.fixture
def language_reference_data():
    common_args = {
        "in_scheme": "http://lexvo.org/id/",
    }
    factories.LanguageFactory(
        url="http://lexvo.org/id/iso639-3/fin",
        pref_label={
            "en": "Finnish",
            "fi": "Suomen kieli",
            "sv": "finska",
            "und": "Finnish",
        },
        **common_args,
    )
    factories.LanguageFactory(
        url="http://lexvo.org/id/iso639-3/eng",
        pref_label={
            "en": "English",
            "fi": "englannin kieli",
            "sv": "engelska",
            "und": "English",
        },
        **common_args,
    )
    factories.LanguageFactory(
        url="http://lexvo.org/id/iso639-3/swe",
        pref_label={
            "en": "Swedish",
            "fi": "ruotsin kieli",
            "sv": "svenska",
            "und": "Swedish",
        },
        **common_args,
    )


@pytest.fixture
def license_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/license",
    }
    factories.LicenseFactory(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0",
        pref_label={
            "fi": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
            "en": "Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
            "und": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
        },
        **common_args,
    )
    factories.LicenseFactory(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
        pref_label={
            "en": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "fi": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
        },
        **common_args,
    )
    factories.LicenseFactory(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/other",
        pref_label={
            "en": "Other",
            "fi": "Muu",
        },
        **common_args,
    )
    factories.LicenseFactory(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/other-closed",
        pref_label={
            "en": "Other (Not Open)",
            "fi": "Muu (Ei avoin)",
        },
        **common_args,
    )


@pytest.fixture
def file_type_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/file_type",
    }
    factories.FileTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/file_type/code/video",
        pref_label={"en": "Video", "fi": "Video"},
        **common_args,
    )
    factories.FileTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/file_type/code/image",
        pref_label={"en": "Image", "fi": "Kuva"},
        **common_args,
    )
    factories.FileTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/file_type/code/text",
        pref_label={"en": "Text", "fi": "Teksti"},
        **common_args,
    )


@pytest.fixture
def use_category_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/use_category",
    }
    factories.UseCategoryFactory(
        url="http://uri.suomi.fi/codelist/fairdata/use_category/code/source",
        pref_label={"en": "Source material", "fi": "Lähdeaineisto"},
        **common_args,
    )
    factories.UseCategoryFactory(
        url="http://uri.suomi.fi/codelist/fairdata/use_category/code/outcome",
        pref_label={"en": "Outcome material", "fi": "Tulosaineisto"},
        **common_args,
    )
    factories.UseCategoryFactory(
        url="http://uri.suomi.fi/codelist/fairdata/use_category/code/documentation",
        pref_label={"en": "Documentation", "fi": "Dokumentaatio"},
        **common_args,
    )


@pytest.fixture
def location_reference_data():
    common_args = {
        "in_scheme": "http://www.yso.fi/onto/yso/places",
    }
    factories.LocationFactory(
        url="http://www.yso.fi/onto/onto/yso/c_9908ce39",
        pref_label={"fi": "Alppikylä (Helsinki)", "sv": "Alpbyn (Helsingfors)"},
        **common_args,
    )
    factories.LocationFactory(
        url="http://www.yso.fi/onto/yso/p105080",
        pref_label={"en": "Koitajoki", "fi": "Koitajoki", "sv": "Koitajoki"},
        **common_args,
    )
    factories.LocationFactory(
        url="http://www.yso.fi/onto/yso/p105747",
        pref_label={"en": "Tapiola", "fi": "Tapiola (Espoo)", "sv": "Hagalund (Esbo)"},
        **common_args,
    )
    factories.LocationFactory(
        url="http://www.yso.fi/onto/yso/p189359",
        pref_label={
            "en": "Unioninkatu",
            "fi": "Unioninkatu (Helsinki)",
            "sv": "Unionsgatan (Helsingfors)",
        },
        **common_args,
    )


@pytest.fixture
def identifier_type_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/identifier_type"}
    factories.IdentifierTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/doi",
        pref_label={"en": "Digital Object Identifier (DOI)"},
        **common_args,
    )
    factories.IdentifierTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/identifier_type/code/urn",
        pref_label={"en": "Uniform Resource Name (URN)"},
        **common_args,
    )


@pytest.fixture
def event_outcome_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/event_outcome"}
    factories.EventOutcomeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/event_outcome/code/success",
        pref_label={"en": "Success", "fi": "Onnistunut", "sv": "Framgångsrik"},
        **common_args,
    )


@pytest.fixture
def lifecycle_event_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/lifecycle_event"}
    factories.LifecycleEventFactory(
        url="http://uri.suomi.fi/codelist/fairdata/lifecycle_event/code/planned",
        pref_label={"en": "Planned", "fi": "Suunniteltu"},
        **common_args,
    )
    factories.LifecycleEventFactory(
        url="http://uri.suomi.fi/codelist/fairdata/lifecycle_event/code/modified",
        pref_label={"en": "Modified", "fi": "Muokattu"},
        **common_args,
    )
    factories.LifecycleEventFactory(
        url="http://uri.suomi.fi/codelist/fairdata/lifecycle_event/code/destroyed",
        pref_label={"en": "Destroyed", "fi": "Tuhottu"},
        **common_args,
    )


@pytest.fixture
def reference_data(
    access_type_reference_data,
    field_of_science_reference_data,
    theme_reference_data,
    language_reference_data,
    license_reference_data,
    file_type_reference_data,
    use_category_reference_data,
    location_reference_data,
    identifier_type_reference_data,
    event_outcome_reference_data,
    lifecycle_event_reference_data,
):
    """Collection of reference data"""


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def requests_client():
    return RequestsClient()


@pytest.fixture(autouse=True)
def tweaked_settings(settings):
    import logging

    logging.disable(logging.CRITICAL)
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
    settings.DEBUG = False
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
    settings.MIDDLEWARE = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "simple_history.middleware.HistoryRequestMiddleware",
    ]
    settings.ENABLE_DEBUG_TOOLBAR = False
    settings.ENABLE_SILK_PROFILER = False
    settings.TEMPLATE_DEBUG = False
