import pytest

from apps.core.models import (
    DatasetLanguage,
    CatalogHomePage,
    DatasetPublisher,
    DatasetLicense,
    AccessType,
    AccessRight,
    DataCatalog,
)


@pytest.fixture
def dataset_language() -> DatasetLanguage:
    identifier = "http://lexvo.org/id/iso639-3/fin"
    title = {
        "en": "Finnish language",
        "fi": "Suomen kieli",
        "sv": "finska",
        "und": "Suomen kieli",
    }
    return DatasetLanguage(
        id=identifier,
        title=title,
    )


@pytest.fixture
def catalog_homepage() -> CatalogHomePage:
    identifier = "https://www.fairdata.fi"
    title = {"fi": "Fairdata.fi", "en": "Fairdata.fi"}

    return CatalogHomePage(id=identifier, title=title)


@pytest.fixture
def dataset_publisher() -> DatasetPublisher:
    name = {
        "en": "Ministry of Education and Culture, Finland",
        "fi": "Opetus- ja kulttuuriministeriö",
    }
    return DatasetPublisher(name=name)


@pytest.fixture
def dataset_license() -> DatasetLicense:
    title = {
        "fi": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
        "en": "Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "und": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
    }
    license = "https://creativecommons.org/publicdomain/zero/1.0/"
    identifier = "http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0"

    return DatasetLicense(title=title, id=identifier, license=license)


@pytest.fixture
def access_type() -> AccessType:
    identifier = "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
    title = {"en": "Open", "fi": "Avoin", "und": "Avoin"}
    return AccessType(id=identifier, title=title)


@pytest.fixture
def access_rights() -> AccessRight:
    description = {
        "en": "Datasets stored in the IDA service",
        "fi": "IDA-palvelussa säilytettävät aineistot",
    }
    return AccessRight(description=description)


@pytest.fixture
def data_catalog() -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-ida"
    title = {
        "en": "Fairdata IDA datasets",
        "fi": "Fairdata IDA-aineistot",
        "sv": "Fairdata forskningsdata",
    }
    return DataCatalog(id=identifier, title=title)
