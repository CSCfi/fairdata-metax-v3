import pytest

from apps.core.models import (
    DatasetLanguage,
    CatalogHomePage,
    DatasetPublisher,
    DatasetLicense,
    AccessType,
    AccessRight,
    DataCatalog,
    CatalogRecord,
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
def access_rights_with_license_and_access_type(
    access_rights, access_type, dataset_license
) -> AccessRight:
    access_type.save()
    dataset_license.save()
    access_rights.license = dataset_license
    access_rights.access_type = access_type
    access_rights.save()
    return access_rights


@pytest.fixture
def data_catalog() -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-ida"
    title = {
        "en": "Fairdata IDA datasets",
        "fi": "Fairdata IDA-aineistot",
        "sv": "Fairdata forskningsdata",
    }
    return DataCatalog(id=identifier, title=title)


@pytest.fixture
def data_catalog_with_foreign_keys(
    dataset_language, dataset_publisher, access_rights, data_catalog
) -> DataCatalog:
    dataset_language.save()
    dataset_publisher.save()
    access_rights.save()
    data_catalog.access_rights = access_rights
    data_catalog.publisher = dataset_publisher
    data_catalog.language.add(dataset_language)
    data_catalog.save()
    return data_catalog


@pytest.fixture
def catalog_record(data_catalog_with_foreign_keys) -> CatalogRecord:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19d7"
    return CatalogRecord(id=identifier, data_catalog=data_catalog_with_foreign_keys)


@pytest.fixture
def dataset_property_object_factory(
    dataset_language, dataset_license, catalog_homepage, access_type, data_catalog
):
    def _dataset_property_object_factory(object_name):
        if object_name == "dataset_language":
            return dataset_language
        elif object_name == "dataset_license":
            return dataset_license
        elif object_name == "catalog_homepage":
            return catalog_homepage
        elif object_name == "access_type":
            return access_type
        elif object_name == "data_catalog":
            return data_catalog

    return _dataset_property_object_factory


@pytest.fixture
def abstract_base_object_factory(dataset_publisher, access_rights, catalog_record):
    def _abstract_base_object_factory(object_name):
        if object_name == "dataset_publisher":
            return dataset_publisher
        elif object_name == "access_rights":
            return access_rights
        elif object_name == "catalog_record":
            return catalog_record

    return _abstract_base_object_factory
