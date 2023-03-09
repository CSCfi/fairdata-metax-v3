import pytest

from apps.core import factories
from apps.core.models import (
    AccessRights,
    AccessType,
    CatalogHomePage,
    CatalogRecord,
    Contract,
    DataCatalog,
    Dataset,
    DatasetPublisher,
    FieldOfScience,
    Language,
    License,
    Theme,
)
from apps.files.factories import FileFactory
from apps.files.models import File, FileStorage


@pytest.fixture
def catalog_homepage() -> CatalogHomePage:
    identifier = "https://www.fairdata.fi"
    title = {"fi": "Fairdata.fi", "en": "Fairdata.fi"}

    return factories.CatalogHomePageFactory(url=identifier, title=title)


@pytest.fixture
def dataset_publisher() -> DatasetPublisher:
    name = {
        "en": "Ministry of Education and Culture, Finland",
        "fi": "Opetus- ja kulttuuriministeriö",
    }
    return factories.DatasetPublisherFactory(name=name)


@pytest.fixture
def access_rights() -> AccessRights:
    description = {
        "en": "Datasets stored in the IDA service",
        "fi": "IDA-palvelussa säilytettävät aineistot",
    }
    return factories.AccessRightsFactory(description=description)


@pytest.fixture
def access_type() -> AccessType:
    identifier = "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
    pref_label = {"en": "Open", "fi": "Avoin", "und": "Avoin"}
    return factories.AccessTypeFactory(url=identifier, pref_label=pref_label)


@pytest.fixture
def field_of_science() -> FieldOfScience:
    return factories.FieldOfScienceFactory(
        url="http://lexvo.org/id/iso639-3/fin",
        pref_label={
            "en": "Finnish",
            "fi": "Suomen kieli",
            "sv": "finska",
            "und": "Finnish",
        },
    )


@pytest.fixture
def keyword() -> Theme:
    return factories.ThemeFactory(
        url="http://www.yso.fi/onto/koko/p1",
        pref_label={
            "en": "data systems designers",
            "fi": "atk-suunnittelijat",
            "sv": "adb-planerare",
        },
    )


@pytest.fixture
def language() -> Language:
    identifier = "http://lexvo.org/id/iso639-3/fin"
    pref_label = {
        "en": "Finnish",
        "fi": "Suomen kieli",
        "sv": "finska",
        "und": "Finnish",
    }
    return factories.LanguageFactory(
        url=identifier,
        pref_label=pref_label,
    )


@pytest.fixture
def license() -> License:
    pref_label = {
        "fi": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
        "en": "Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "und": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
    }
    identifier = "http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0"

    return factories.LicenseFactory(pref_label=pref_label, url=identifier)


@pytest.fixture
def contract() -> Contract:
    title = {
        "en": "Title 5",
        "fi": "Otsikko 5",
        "sv": "Titel 5",
    }
    quota = 111204
    valid_from = "2023-12-31 15:25:00+01"
    return Contract(title=title, quota=quota, valid_until=valid_from)


@pytest.fixture
def catalog_record(data_catalog) -> CatalogRecord:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19d7"
    return factories.CatalogRecordFactory(id=identifier, data_catalog=data_catalog)


@pytest.fixture
def dataset() -> Dataset:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca37d7"
    title = {
        "en": "Title 2",
        "fi": "Otsikko 2",
        "sv": "Titel 2",
    }
    return factories.DatasetFactory(id=identifier, title=title)


@pytest.fixture
def dataset_with_foreign_keys(
    access_rights, language, field_of_science, keyword, dataset, data_catalog
) -> Dataset:
    datasets = list(factories.DatasetFactory.create_batch(4))
    dataset.data_catalog = data_catalog
    dataset.access_rights = access_rights
    dataset.first = datasets[0]
    dataset.last = datasets[1]
    dataset.previous = datasets[2]
    dataset.replaces = datasets[3]
    dataset.first.data_catalog = data_catalog
    dataset.last.data_catalog = data_catalog
    dataset.previous.data_catalog = data_catalog
    dataset.replaces.data_catalog = data_catalog
    dataset.first.save()
    dataset.last.save()
    dataset.previous.save()
    dataset.replaces.save()
    dataset.save()
    dataset.language.add(language)
    dataset.field_of_science.add(field_of_science)
    dataset.theme.add(keyword)
    return dataset


@pytest.fixture
def catalog_record(data_catalog, contract) -> CatalogRecord:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19d7"
    contract.save()
    return CatalogRecord(id=identifier, data_catalog=data_catalog, contract=contract)


@pytest.fixture
def file_storage() -> FileStorage:
    identifier = "test-data-storage"
    endpoint_url = "https://www.test-123456dcba.fi"
    endpoint_description = "Test-Data-Storage that is used for testing files"
    return factories.FileStorageFactory(
        id=identifier,
        endpoint_url=endpoint_url,
        endpoint_description=endpoint_description,
    )


@pytest.fixture
def file() -> File:
    byte_size = 999
    checksum = "ABC-123456"
    file_path = "/project_x/path/file.pdf"
    date_uploaded = "2021-12-31 15:25:00+01"
    file_modified = "2021-12-31 12:25:00+01"
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19e7"
    return FileFactory(
        byte_size=byte_size,
        checksum_value=checksum,
        file_path=file_path,
        file_modified=file_modified,
        date_uploaded=date_uploaded,
        id=identifier,
    )


@pytest.fixture
def dataset_property_object_factory(
    catalog_homepage,
    data_catalog,
):
    def _dataset_property_object_factory(object_name):
        if object_name == "catalog_homepage":
            return catalog_homepage
        elif object_name == "data_catalog":
            return data_catalog

    return _dataset_property_object_factory


@pytest.fixture
def abstract_base_object_factory(
    dataset_publisher, access_rights, catalog_record, file_storage, file, contract
):
    def _abstract_base_object_factory(object_name):
        if object_name == "dataset_publisher":
            return dataset_publisher
        elif object_name == "access_rights":
            return access_rights
        elif object_name == "catalog_record":
            return catalog_record
        elif object_name == "file_storage":
            return file_storage
        elif object_name == "file":
            return file
        elif object_name == "contract":
            return contract

    return _abstract_base_object_factory
