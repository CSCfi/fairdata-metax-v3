import pytest

from apps.core import factories
from apps.core.models.catalog_record.dataset_index import EntryTuple
from apps.core.models import (
    AccessType,
    FieldOfScience,
    ResearchInfra,
    FileSetFileMetadata,
    FileType,
)
from apps.files.factories import FileFactory

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def all_facets_dataset(reference_data, data_catalog):
    """Dataset that has values for all facets."""
    # data_catalog, access_type, keyword
    dataset = factories.DatasetFactory(
        data_catalog=data_catalog,
        access_rights__access_type=AccessType.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/access_type/code/open"
        ),
        keyword=["hello", "world"],
    )

    # creator, organization
    creator = factories.DatasetActorFactory(
        organization=factories.OrganizationFactory(
            pref_label={"en": "Organization", "fi": "Organisaatio"}
        ),
        person=factories.PersonFactory(name="Luoja"),
        roles=["creator", "publisher"],
    )
    contributor = factories.DatasetActorFactory(
        organization=factories.OrganizationFactory(pref_label={"en": "Contributor org"}),
        person=factories.PersonFactory(name="Ei Luoja"),
        roles=["contributor"],
    )
    dataset.actors.set([creator, contributor])

    # field_of_science
    dataset.field_of_science.set(
        [
            FieldOfScience.objects.get(url="http://www.yso.fi/onto/okm-tieteenala/ta111"),
            FieldOfScience.objects.get(url="http://www.yso.fi/onto/okm-tieteenala/ta112"),
        ]
    )

    # infrastructure
    infra = ResearchInfra.objects.create(
        url="http://www.example.com/infras/1",
        in_scheme="http://www.example.com/infras",
        pref_label={"en": "Infra 1"},
    )
    infra2 = ResearchInfra.objects.create(  # test that coalesce for unknown language works
        url="http://www.example.com/infras/2",
        in_scheme="http://www.example.com/infras",
        pref_label={"xyz": "Infra 2 in some unknown language"},
    )
    dataset.infrastructure.add(infra, infra2)

    # project
    project = factories.DatasetProjectFactory(title={"en": "Project", "fi": "Projekti"})
    dataset.projects.add(project)

    # file_type
    fileset = factories.FileSetFactory(dataset=dataset)
    file = FileFactory()
    fileset.files.set([file])
    FileSetFileMetadata.objects.create(
        file_set=fileset,
        file=file,
        file_type=FileType.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/file_type/code/image"
        ),
    )
    dataset.fileset = fileset
    return dataset


def test_dataset_update_index_for_facets(all_facets_dataset):
    tuples = EntryTuple.from_entries(all_facets_dataset.update_index())
    tuples = sorted(
        (t.key, t.language, t.value) for t in tuples
    )  # reorganize fields and sort for easier testing
    expected = [
        ("access_type", "en", "Open"),
        ("access_type", "fi", "Avoin"),
        ("creator", "en", "Luoja"),
        ("creator", "en", "Organization"),
        ("creator", "fi", "Luoja"),
        ("creator", "fi", "Organisaatio"),
        ("data_catalog", "en", "Fairdata IDA datasets"),
        ("data_catalog", "fi", "Fairdata IDA-aineistot"),
        ("field_of_science", "en", "Mathematics"),
        ("field_of_science", "en", "Statistics and probability"),
        ("field_of_science", "fi", "Matematiikka"),
        ("field_of_science", "fi", "Tilastotiede"),
        ("file_type", "en", "Image"),
        ("file_type", "fi", "Kuva"),
        ("infrastructure", "en", "Infra 1"),
        ("infrastructure", "en", "Infra 2 in some unknown language"),
        ("infrastructure", "fi", "Infra 1"),
        ("infrastructure", "fi", "Infra 2 in some unknown language"),
        ("keyword", "en", "hello"),
        ("keyword", "en", "world"),
        ("keyword", "fi", "hello"),
        ("keyword", "fi", "world"),
        ("organization", "en", "Contributor org"),
        ("organization", "en", "Organization"),
        ("organization", "fi", "Contributor org"),
        ("organization", "fi", "Organisaatio"),
        ("project", "en", "Project"),
        ("project", "fi", "Projekti"),
    ]
    assert tuples == expected, f"Entries don't match, {tuples=}"


def test_dataset_update_index_for_no_facets():
    dataset = factories.DatasetFactory(data_catalog=None, access_rights=None)
    tuples = EntryTuple.from_entries(dataset.update_index())
    assert tuples == [], f"Expected no entries, got {tuples=}"
