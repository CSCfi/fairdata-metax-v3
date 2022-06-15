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
    DataStorage,
    File,
    Distribution,
    ResearchDataset,
    Contract,
)
from apps.core import factories


@pytest.fixture
def dataset_language() -> DatasetLanguage:
    identifier = "http://lexvo.org/id/iso639-3/fin"
    title = {
        "en": "Finnish language",
        "fi": "Suomen kieli",
        "sv": "finska",
        "und": "Suomen kieli",
    }
    return factories.LanguageFactory(
        url=identifier,
        title=title,
    )


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
def dataset_license() -> DatasetLicense:
    title = {
        "fi": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
        "en": "Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "und": "Creative Commons Yleismaailmallinen (CC0 1.0) Public Domain -lausuma",
    }
    identifier = "http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0"

    return factories.DatasetLicenseFactory(title=title, url=identifier)


@pytest.fixture
def access_type() -> AccessType:
    identifier = "http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
    title = {"en": "Open", "fi": "Avoin", "und": "Avoin"}
    return factories.AccessTypeFactory(url=identifier, title=title)


@pytest.fixture
def access_rights() -> AccessRight:
    description = {
        "en": "Datasets stored in the IDA service",
        "fi": "IDA-palvelussa säilytettävät aineistot",
    }
    return factories.AccessRightFactory(description=description)

@pytest.fixture
def contract() -> Contract:
    title = {
        "en": "Title 5",
        "fi": "Otsikko 5",
        "sv": "Titel 5",
    }
    quota = 111204
    valid_until = "2023-12-31 15:25:00+01"
    return Contract(title=title, quota=quota, valid_until=valid_until)

@pytest.fixture
def data_catalog() -> DataCatalog:
    identifier = "urn:nbn:fi:att:data-catalog-ida"
    title = {
        "en": "Fairdata IDA datasets",
        "fi": "Fairdata IDA-aineistot",
        "sv": "Fairdata forskningsdata",
    }
    return factories.DataCatalogFactory(id=identifier, title=title)


@pytest.fixture
def catalog_record(data_catalog) -> CatalogRecord:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19d7"
    return factories.CatalogRecordFactory(id=identifier, data_catalog=data_catalog)


@pytest.fixture
def research_dataset() -> ResearchDataset:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca37d7"
    title = {
        "en": "Title 2",
        "fi": "Otsikko 2",
        "sv": "Titel 2",
    }
    return factories.ResearchDatasetFactory(id=identifier, title=title)


@pytest.fixture
def research_dataset_with_foreign_keys(
    access_rights, dataset_language, research_dataset, data_catalog
) -> ResearchDataset:
    research_datasets = list(factories.ResearchDatasetFactory.create_batch(4))
    research_dataset.data_catalog = data_catalog
    research_dataset.access_right = access_rights
    research_dataset.first = research_datasets[0]
    research_dataset.last = research_datasets[1]
    research_dataset.previous = research_datasets[2]
    research_dataset.replaces = research_datasets[3]
    research_dataset.first.data_catalog = data_catalog
    research_dataset.last.data_catalog = data_catalog
    research_dataset.previous.data_catalog = data_catalog
    research_dataset.replaces.data_catalog = data_catalog
    research_dataset.first.save()
    research_dataset.last.save()
    research_dataset.previous.save()
    research_dataset.replaces.save()
    research_dataset.save()
    research_dataset.language.add(dataset_language)
    return research_dataset

@pytest.fixture
def catalog_record(data_catalog, contract) -> CatalogRecord:
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19d7"
    contract.save()
    return CatalogRecord(id=identifier, data_catalog=data_catalog, contract=contract)

@pytest.fixture
def data_storage() -> DataStorage:
    identifier = "test-data-storage"
    endpoint_url = "https://www.test-123456dcba.fi"
    endpoint_description = "Test-Data-Storage that is used for testing files"
    return factories.DataStorageFactory(
        id=identifier,
        endpoint_url=endpoint_url,
        endpoint_description=endpoint_description,
    )


@pytest.fixture
def distribution() -> Distribution:
    identifier = "abcd1234"
    title = {
        "en": "Title",
        "fi": "Otsikko",
        "sv": "Titel",
    }
    access_url = "https://www.test123321abc.fi"
    download_url = "https://www.test321123abc.fi"
    byte_size = 999999
    checksum = "ABC-12345"
    return factories.DistributionFactory(
        id=identifier,
        title=title,
        access_url=access_url,
        download_url=download_url,
        byte_size=byte_size,
        checksum=checksum,
    )


@pytest.fixture
def file() -> File:
    byte_size = 999
    checksum = "ABC-123456"
    file_name = "awesome_file_name"
    file_path = "/project_x/path/file.pdf"
    date_uploaded = "2021-12-31 15:25:00+01"
    identifier = "12345678-51d3-4c25-ad20-75aff8ca19e7"
    return factories.FileFactory(
        byte_size=byte_size,
        checksum=checksum,
        file_name=file_name,
        file_path=file_path,
        date_uploaded=date_uploaded,
        id=identifier,
    )


@pytest.fixture
def dataset_property_object_factory(
    dataset_language,
    dataset_license,
    catalog_homepage,
    access_type,
    data_catalog,
    distribution,
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
        elif object_name == "distribution":
            return distribution

    return _dataset_property_object_factory


@pytest.fixture
def abstract_base_object_factory(dataset_publisher, access_rights, catalog_record, data_storage, file, contract):
    def _abstract_base_object_factory(object_name):
        if object_name == "dataset_publisher":
            return dataset_publisher
        elif object_name == "access_rights":
            return access_rights
        elif object_name == "catalog_record":
            return catalog_record
        elif object_name == "data_storage":
            return data_storage
        elif object_name == "file":
            return file
        elif object_name == "contract":
            return contract

    return _abstract_base_object_factory
