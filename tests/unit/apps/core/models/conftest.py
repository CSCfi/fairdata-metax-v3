import pytest

from apps.core import factories
from apps.core.models import (
    AccessRights,
    AccessType,
    CatalogHomePage,
    Contract,
    Dataset,
    DatasetLicense,
    DatasetPublisher,
    FieldOfScience,
    Language,
    MetadataProvider,
    ResearchInfra,
    Theme,
)
from apps.files.factories import FileFactory
from apps.files.models import File


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
def metadata_provider() -> MetadataProvider:
    organization = "Awesome Organization"
    return factories.MetadataProviderFactory(organization=organization)


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
def infrastructure() -> ResearchInfra:
    return factories.InfrastructureFactory(
        url="http://www.yso.fi/onto/koko/p34158/data/1234",
        pref_label={
            "en": "Infra",
            "fi": "Infrä",
            "sv": "Infrå",
            "und": "Infra",
        },
    )


@pytest.fixture
def theme() -> Theme:
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
def license() -> DatasetLicense:
    return factories.DatasetLicenseFactory()


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
def dataset() -> Dataset:
    title = {
        "en": "Title 2",
        "fi": "Otsikko 2",
        "sv": "Titel 2",
    }
    persistent_id = "doi:1234"
    catalog = factories.DataCatalogFactory(dataset_versioning_enabled=True)
    dataset = factories.DatasetFactory(
        title=title,
        cumulative_state=1,
        persistent_identifier=persistent_id,
        data_catalog=catalog,
    )
    dataset.actors.add(factories.DatasetActorFactory(roles=["creator", "publisher"], dataset=None))
    return dataset


@pytest.fixture
def dataset_with_foreign_keys(
    access_rights, language, field_of_science, theme, dataset, data_catalog
) -> Dataset:
    dataset.data_catalog = data_catalog
    dataset.access_rights = access_rights
    dataset.save()
    dataset.language.add(language)
    dataset.field_of_science.add(field_of_science)
    dataset.theme.add(theme)
    dataset.publish()
    return dataset


@pytest.fixture
def file() -> File:
    size = 999
    checksum = "md5:abc_123456"
    pathname = "/project_x/path/file.pdf"
    modified = "2021-12-31 12:25:00+01"
    id = "12345678-51d3-4c25-ad20-75aff8ca19e7"
    return FileFactory(
        size=size,
        checksum_value=checksum,
        pathname=pathname,
        modified=modified,
        id=id,
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
    dataset_publisher, access_rights, file, contract, metadata_provider
):
    def _abstract_base_object_factory(object_name):
        if object_name == "dataset_publisher":
            return dataset_publisher
        elif object_name == "access_rights":
            return access_rights
        elif object_name == "file":
            return file
        elif object_name == "contract":
            return contract
        elif object_name == "metadata_provider":
            return metadata_provider

    return _abstract_base_object_factory
