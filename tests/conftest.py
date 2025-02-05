# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for metax_service.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import Mock

import django
import factory.random
import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import caches
from django.dispatch import receiver
from django.test.client import Client
from rest_framework.test import APIClient, RequestsClient

from apps.core import factories
from apps.core.models.contract import Contract
from apps.core.models.data_catalog import DataCatalog
from apps.core.signals import dataset_created, dataset_updated
from apps.files import factories as files_factories
from apps.users.factories import MetaxUserFactory
from apps.users.models import MetaxUser


@dataclass
class DatasetSignalHandlers:
    created: Mock = field(default_factory=lambda: Mock(spec=[]))
    updated: Mock = field(default_factory=lambda: Mock(spec=[]))

    def reset(self):
        """Reset mock calls."""
        self.created.reset_mock()
        self.updated.reset_mock()

    def assert_call_counts(self, created: Optional[int] = None, updated: Optional[int] = None):
        if created is not None:
            assert self.created.call_count == created
        if updated is not None:
            assert self.updated.call_count == updated


@pytest.fixture()
def dataset_signal_handlers() -> DatasetSignalHandlers:
    handlers = DatasetSignalHandlers()
    receiver(dataset_created, weak=True)(handlers.created)
    receiver(dataset_updated, weak=True)(handlers.updated)
    return handlers


@pytest.fixture
def enable_sso(settings):
    settings.ENABLE_SSO_AUTH = True
    settings.SSO_SECRET_KEY = "TOP_SECRET"
    settings.SSO_SESSION_COOKIE = "sso_session_test"
    settings.SSO_HOST = "https://fake-sso"
    settings.SSO_METAX_SERVICE_NAME = "METAX"
    settings.SSO_TRUSTED_SERVICE_TOKEN = "trusted-token"


@pytest.fixture
def disable_sso(settings):
    settings.ENABLE_SSO_AUTH = False


@pytest.fixture
def fairdata_users_group():
    group, _ = Group.objects.get_or_create(name="fairdata_users")
    return group


@pytest.fixture
def service_group():
    group, _ = Group.objects.get_or_create(name="service")
    return group


@pytest.fixture
def pas_group():
    group, _ = Group.objects.get_or_create(name="pas")
    return group


@pytest.fixture
def ida_group():
    group, _ = Group.objects.get_or_create(name="ida")
    return group


@pytest.fixture
def user(fairdata_users_group):
    user, created = MetaxUser.objects.get_or_create(
        username="test_user",
        fairdata_username="test_user",
        first_name="Teppo",
        last_name="Testaaja",
        email="teppo@example.com",
        is_hidden=False,
    )
    user.groups.set([fairdata_users_group])
    user.set_password("teppo")
    user.save()
    return user


@pytest.fixture
def user2(fairdata_users_group):
    user, _created = MetaxUser.objects.get_or_create(
        username="test_user2",
        fairdata_username="test_user2",
        first_name="Matti",
        last_name="Mestaaja",
        email="matti@example.com",
        is_hidden=False,
    )
    _group, _ = Group.objects.get_or_create(name="fairdata_users")
    user.groups.set([fairdata_users_group])
    user.set_password("matti")
    user.save()
    return user


@pytest.fixture(scope="session", autouse=True)
def faker_session_locale():
    return ["en_US"]


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return settings.FACTORY_BOY_RANDOM_SEED


@pytest.fixture
def service_client():
    client = Client()
    user = MetaxUserFactory(username="service_test")
    group_service, _ = Group.objects.get_or_create(name="service")
    group_test, _ = Group.objects.get_or_create(name="test")
    user.groups.set([group_test, group_service])
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def ida_client():
    client = Client()
    user = MetaxUserFactory(username="service_test_ida")
    service_group, _ = Group.objects.get_or_create(name="service")
    ida_group, _ = Group.objects.get_or_create(name="ida")
    user.groups.set([service_group, ida_group])
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def pas_client():
    client = Client()
    user = MetaxUserFactory(username="service_test_pas")
    service_group, _ = Group.objects.get_or_create(name="service")
    pas_group, _ = Group.objects.get_or_create(name="pas")
    user.groups.set([service_group, pas_group])
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def v2_migration_client():
    client = Client()
    user = MetaxUserFactory(username="service_test_v2_migration")
    service_group, _ = Group.objects.get_or_create(name="service")
    pas_group, _ = Group.objects.get_or_create(name="v2_migration")
    user.groups.set([service_group, pas_group])
    client.force_login(user)
    return client


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

    # When some tests contain @pytest.mark.only, run only those tests.
    only = [item for item in items if item.get_closest_marker("only")]
    if only:
        items[:] = only


@pytest.fixture
def data_catalog(fairdata_users_group, service_group, pas_group, ida_group) -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-ida"
    title = {
        "en": "Fairdata IDA datasets",
        "fi": "Fairdata IDA-aineistot",
        "sv": "Fairdata forskningsdata",
    }
    catalog = factories.DataCatalogFactory(
        id=identifier,
        title=title,
        dataset_versioning_enabled=True,
        allow_remote_resources=True,
        storage_services=["ida", "pas"],
        allowed_pid_types=["URN", "DOI"],
    )
    catalog.dataset_groups_create.set([fairdata_users_group, service_group])
    catalog.dataset_groups_admin.set([pas_group, ida_group])
    return catalog


@pytest.fixture
def data_catalog_att(fairdata_users_group, service_group) -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-att"
    title = {
        "en": "Fairdata ATT datasets",
        "fi": "Fairdata ATT-aineistot",
    }
    catalog = factories.DataCatalogFactory(
        id=identifier,
        title=title,
        dataset_versioning_enabled=True,
        allow_remote_resources=True,
        allowed_pid_types=["URN"],
    )
    catalog.dataset_groups_create.set([fairdata_users_group, service_group])
    return catalog


@pytest.fixture
def data_catalog_pas(pas_group) -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-pas"
    title = {
        "en": "Fairdata PAS datasets",
        "fi": "Fairdata PAS-aineistot",
    }
    catalog = factories.DataCatalogFactory(
        id=identifier,
        title=title,
        dataset_versioning_enabled=False,
        allow_remote_resources=False,
        allowed_pid_types=["URN", "DOI"],
        storage_services=["pas"],
    )
    catalog.dataset_groups_create.set([pas_group])
    catalog.dataset_groups_admin.set([pas_group])
    return catalog


@pytest.fixture
def data_catalog_harvested(fairdata_users_group, service_group) -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-harvested"
    title = {
        "en": "Harvested datasets",
    }
    catalog = factories.DataCatalogFactory(
        id=identifier,
        title=title,
        is_external=True,
        allow_remote_resources=True,
    )
    catalog.dataset_groups_create.set([fairdata_users_group, service_group])
    return catalog


@pytest.fixture
def data_catalog_harvested_b(fairdata_users_group, service_group) -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-harvested_b"
    title = {
        "en": "Harvested datasets",
    }
    catalog = factories.DataCatalogFactory(
        id=identifier,
        title=title,
        is_external=True,
        allow_remote_resources=True,
    )
    catalog.dataset_groups_create.set([fairdata_users_group, service_group])
    return catalog


@pytest.fixture
def contract() -> Contract:
    _id = "urn:nbn:fi:contract:test-contract-1"
    title = {
        "en": "Title 5",
        "fi": "Otsikko 5",
        "sv": "Titel 5",
    }
    quota = 111204
    valid_from = "2023-06-15"
    valid_until = "2023-12-31"
    created = "2021-12-31T12:13:14Z"
    modified = "2021-12-31T12:13:14Z"
    return Contract.objects.create(
        id=_id,
        created=created,
        modified=modified,
        title=title,
        quota=quota,
        validity_start_date=valid_from,
        validity_end_date=valid_until,
        legacy_id=1,
    )


@pytest.fixture
def organization_reference_data():
    scheme = settings.ORGANIZATION_SCHEME
    return [
        factories.OrganizationFactory(
            pref_label={"en": "Aalto University", "fi": "Aalto-yliopisto"},
            in_scheme=scheme,
            url="http://uri.suomi.fi/codelist/fairdata/organization/code/10076",
        ),
        factories.OrganizationFactory(
            pref_label={"en": "Kone Foundation", "fi": "Koneen Säätiö"},
            in_scheme=scheme,
            url="http://uri.suomi.fi/codelist/fairdata/organization/code/02135371",
        ),
        factories.OrganizationFactory(
            pref_label={
                "en": "CSC – IT Center for Science",
                "fi": "CSC - Tieteen tietotekniikan keskus Oy",
                "sv": "CSC – IT Center for Science",
                "und": "CSC - Tieteen tietotekniikan keskus Oy",
            },
            url="http://uri.suomi.fi/codelist/fairdata/organization/code/09206320",
            in_scheme="http://uri.suomi.fi/codelist/fairdata/organization",
        ),
    ]


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
def restriction_grounds_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds",
    }
    factories.RestrictionGroundsFactory(
        url="http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/environmental",
        pref_label={
            "en": "Restricted access due to environmental preservation reasons",
            "fi": "Saatavuutta rajoitettu luonnonsuojelun perusteella",
        },
        **common_args,
    )
    factories.RestrictionGroundsFactory(
        url="http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research",
        pref_label={
            "en": "Restriced access for research based on contract",
            "fi": "Saatavuutta rajoitettu sopimuksen perusteella vain tutkimuskäyttöön",
        },
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
def file_format_reference_data():
    common_args = {
        "in_scheme": "http://uri.suomi.fi/codelist/fairdata/file_format_version",
    }
    files_factories.FileFormatVersionFactory(
        url="http://uri.suomi.fi/codelist/fairdata/file_format_version/code/text_csv",
        pref_label={"en": "text/csv", "fi": "text/csv"},
        file_format="text/csv",
        format_version="",
        **common_args,
    )
    files_factories.FileFormatVersionFactory(
        url="http://uri.suomi.fi/codelist/fairdata/file_format_version/code/application_pdf_1.2",
        pref_label={
            "en": "application/pdf 1.2",
            "fi": "application/pdf 1.2",
        },
        file_format="application/pdf",
        format_version="1.2",
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
def resource_type_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/resource_type"}
    factories.ResourceTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/resource_type/code/sound",
        pref_label={"en": "Sound", "fi": "Ääni"},
        **common_args,
    )
    factories.ResourceTypeFactory(
        url="http://uri.suomi.fi/codelist/fairdata/resource_type/code/dataset",
        pref_label={"en": "Dataset", "fi": "Tutkimusaineisto"},
        **common_args,
    )


@pytest.fixture
def relation_type_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/relation_type"}
    factories.RelationTypeFactory(
        url="http://purl.org/dc/terms/relation",
        pref_label={"en": "Relation", "fi": "Liittyy"},
        **common_args,
    )
    factories.RelationTypeFactory(
        url="http://purl.org/spar/cito/cites",
        pref_label={"en": "Cites", "fi": "Viittaa"},
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
def preservation_event_reference_data():
    common_args = {"in_scheme": "http://uri.suomi.fi/codelist/fairdata/preservation_event"}
    factories.PreservationEventFactory(
        url="http://uri.suomi.fi/codelist/fairdata/preservation_event/code/cre",
        pref_label={"en": "Creation", "fi": "Luonti"},
        **common_args,
    )


@pytest.fixture
def funder_type_reference_data():
    factories.FunderTypeFactory(
        in_scheme="http://uri.suomi.fi/codelist/fairdata/funder_type",
        url="http://uri.suomi.fi/codelist/fairdata/funder_type/code/other-public",
        pref_label={
            "en": "Other public funding",
            "fi": "Muu julkinen rahoitus",
            "und": "Muu julkinen rahoitus",
        },
    )


@pytest.fixture
def reference_data(
    access_type_reference_data,
    restriction_grounds_reference_data,
    field_of_science_reference_data,
    theme_reference_data,
    language_reference_data,
    license_reference_data,
    file_type_reference_data,
    use_category_reference_data,
    location_reference_data,
    identifier_type_reference_data,
    resource_type_reference_data,
    relation_type_reference_data,
    event_outcome_reference_data,
    lifecycle_event_reference_data,
    funder_type_reference_data,
    organization_reference_data,
    preservation_event_reference_data,
    file_format_reference_data,
):
    """Collection of reference data"""


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def requests_client():
    return RequestsClient()


@pytest.fixture
def user_client(user):
    client = Client()
    client._user = user
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def user_client_2(user2):
    client = Client()
    client.force_login(user2)
    client._user = user2
    return client


@pytest.fixture(autouse=True)
def tweaked_settings(settings):
    logging.disable(logging.CRITICAL)
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
        "serialized_datasets": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
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
    settings.METAX_V2_INTEGRATION_ENABLED = False
    settings.METAX_V2_HOST = "metaxv2host"
    settings.ENABLE_SSO_AUTH = False
    settings.METRICS_REPORT_URL = "https://example.com/metrics/reports/datasets.json"
    settings.ENABLE_BACKGROUND_TASKS = False
    settings.PID_MS_CLIENT_INSTANCE = "apps.core.services.pid_ms_client._DummyPIDMSClient"


@pytest.fixture
def v2_integration_settings(settings):
    settings.METAX_V2_INTEGRATION_ENABLED = True
    settings.METAX_V2_HOST = "https://metax-v2-test"
    settings.METAX_V2_USER = "metax-v3-user"
    settings.METAX_V2_PASSWORD = "metax-v3-password"
    return settings


@pytest.fixture
def v2_integration_settings_disabled(v2_integration_settings):
    v2_integration_settings.METAX_V2_INTEGRATION_ENABLED = False
    return v2_integration_settings


@pytest.fixture
def mock_v2_integration(requests_mock, v2_integration_settings):
    matcher = re.compile(v2_integration_settings.METAX_V2_HOST)
    yield {
        "any": requests_mock,
        "post": requests_mock.register_uri("POST", matcher, status_code=201),
        "delete": requests_mock.register_uri("DELETE", matcher, status_code=204),
        "get": requests_mock.register_uri("GET", matcher, status_code=200),
        "put": requests_mock.register_uri("PUT", matcher, status_code=200),
        "patch": requests_mock.register_uri("PATCH", matcher, status_code=200),
    }


mock_store = {}


@pytest.fixture(autouse=True)
def change_pi_url(settings):
    settings.PID_MS_BASEURL = "pidmsbaseurl"


# Insert PID returns the last two parts of the path (i.e. the inserted DOI)
def insert_pid_callback(request, context):
    path = request.path
    path_parts = path.split("/")
    response_text = f"{path_parts[-2]}/{path_parts[-1]}"
    context.status_code = 200
    return response_text


# Create a DOI for a dataset and save the doi and the url to mock_store
def request_doi_callback(request, context):
    doi = f"10.82614/{str(uuid.uuid4())}"
    context.status_code = 201
    dataset_url = request.json()["data"]["attributes"]["url"]
    mock_store[doi] = dataset_url
    return doi


# Read the URL for a sepcific DOI from the mock_store
def get_doi_callback(request, context):
    path = request.path
    path_parts = path.split("/")
    doi = f"{path_parts[-2]}/{path_parts[-1]}"
    if doi in mock_store:
        context.status_code = 200
        return mock_store[doi]
    context.status_code = 404
    return None


@pytest.fixture(autouse=True)
def mock_pid_ms(request, requests_mock, settings):
    if "noautomock" not in request.keywords:
        matcher = re.compile("http://localhost")
        matcher_doi = re.compile(f"https://{settings.PID_MS_BASEURL}/v1/pid/doi/10.(82614|23729)/")
        responselist1 = [
            {"text": f"urn:nbn:fi:att:{str(uuid.uuid4())}", "status_code": 201},
            {"text": f"urn:nbn:fi:att:{str(uuid.uuid4())}", "status_code": 201},
            {"text": f"urn:nbn:fi:att:{str(uuid.uuid4())}", "status_code": 201},
            {"text": f"urn:nbn:fi:att:{str(uuid.uuid4())}", "status_code": 201},
        ]
        responselist3 = [
            {"text": "http://localhost/a", "status_code": 200},
            {"text": "http://localhost/b", "status_code": 200},
        ]
        # Create URN
        requests_mock.register_uri(
            "POST", f"https://{settings.PID_MS_BASEURL}/v1/pid", responselist1
        )
        # Create DOI
        requests_mock.register_uri(
            "POST", f"https://{settings.PID_MS_BASEURL}/v1/pid/doi", text=request_doi_callback
        )
        # Get PID
        requests_mock.register_uri(
            "GET",
            re.compile(f"https://{settings.PID_MS_BASEURL}/get/v1/pid/*"),
            text=get_doi_callback,
        )
        # Insert PID
        requests_mock.register_uri(
            "POST",
            re.compile(f"https://{settings.PID_MS_BASEURL}/v1/pid/10.(82614|23729)/*"),
            text=insert_pid_callback,
        )
        requests_mock.register_uri("PUT", matcher_doi, responselist3)
        requests_mock.register_uri("GET", matcher, real_http=True)
        requests_mock.register_uri("POST", matcher, real_http=True)
        requests_mock.register_uri("PUT", matcher, real_http=True)
        requests_mock.register_uri("PATCH", matcher, real_http=True)
        requests_mock.register_uri("DELETE", matcher, real_http=True)
    yield requests_mock


@pytest.fixture
def dataset_cache(settings):
    """Setup temporary cache for datasets."""
    settings.CACHES["serialized_datasets"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "serialized-datasets",
        "OPTIONS": {"MAX_ENTRIES": 100},
    }
    cache = caches["serialized_datasets"]
    yield cache
    cache.clear()
