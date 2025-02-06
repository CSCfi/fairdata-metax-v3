import pytest
from django.utils import timezone

from apps.core.factories import (
    AccessRightsFactory,
    AccessTypeFactory,
    DatasetActorFactory,
    DatasetFactory,
    DatasetLicenseFactory,
    LanguageFactory,
    PreservationFactory,
    ProvenanceFactory,
    PublishedDatasetFactory,
)
from apps.core.models import Dataset, DatasetVersions

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.versioning]


def test_create_new_version(language, theme, dataset):
    DatasetActorFactory.create_batch(2, dataset=dataset, roles=["creator"])
    ProvenanceFactory(dataset=dataset)
    dataset.language.add(language)
    dataset.theme.add(theme)
    dataset.preservation = PreservationFactory(state=-1)
    dataset.cumulative_state = Dataset.CumulativeState.ACTIVE
    dataset.save()
    dataset.publish()
    dataset.cumulative_state = Dataset.CumulativeState.CLOSED
    dataset.deprecated = timezone.now()
    dataset.save()

    old_version = dataset
    new_version = Dataset.create_new_version(dataset)
    assert new_version.id != old_version.id
    assert new_version.published_revision == 0
    assert old_version.language.all().count() != 0
    assert old_version.theme.all().count() != 0
    assert old_version.actors.all().count() != 0
    assert old_version.language.all().count() == new_version.language.all().count()
    assert old_version.theme.all().count() == new_version.theme.all().count()
    assert old_version.field_of_science.all().count() == new_version.field_of_science.all().count()
    assert old_version.actors.all().count() == new_version.actors.all().count()
    assert old_version.access_rights.id != new_version.access_rights.id
    assert old_version.actors.difference(new_version.actors.all()).count() == 3
    assert old_version.provenance.difference(new_version.provenance.all()).count() == 1
    assert new_version.permissions_id == old_version.permissions_id
    assert new_version.dataset_versions_id == old_version.dataset_versions_id
    assert new_version.cumulative_state == Dataset.CumulativeState.NOT_CUMULATIVE
    assert new_version.deprecated is None

    # Preservation status is reset for new version
    assert old_version.preservation
    assert not new_version.preservation


def test_edit_new_version(dataset_with_foreign_keys):
    lic1 = DatasetLicenseFactory()
    dataset_with_foreign_keys.access_rights = AccessRightsFactory(license=[lic1])
    old_version = dataset_with_foreign_keys
    new_version = Dataset.create_copy(dataset_with_foreign_keys)
    lic2 = DatasetLicenseFactory()
    new_version.title = {"fi": "New title"}
    new_version.language.add(LanguageFactory())
    new_version.access_rights.access_type = AccessTypeFactory(url="http://example.com")
    new_version.access_rights.license.add(lic2)
    new_version.save()
    assert old_version.access_rights.license.all().count() == 1
    assert new_version.access_rights.license.all().count() == 2
    assert (
        new_version.access_rights.license.all().first().id
        != old_version.access_rights.license.all().first().id
    )
    assert new_version.language.all().count() != old_version.language.all().count()


def test_publish_dataset(dataset):
    dataset.publish()
    assert dataset.published_revision == 1
    assert dataset.issued is not None
    dataset.save()
    assert dataset.published_revision == 2
    assert dataset.draft_revision == 0


def test_other_versions(dataset):
    dataset.publish()
    first = dataset
    second = Dataset.create_new_version(first)
    second.persistent_identifier = "doi:10.5678/9"
    second.publish()
    third = Dataset.create_new_version(second)
    assert first.dataset_versions == second.dataset_versions == third.dataset_versions
    assert first.next_existing_version.id == second.id
    assert second.next_existing_version.id == third.id
    assert third.next_existing_version == None
    assert first.created < second.created < third.created


def test_draft_of_dataset_versions():
    dataset = PublishedDatasetFactory()
    with pytest.raises(ValueError) as ec:
        DatasetFactory(draft_of=dataset, dataset_versions=DatasetVersions())
    assert str(ec.value) == "Draft datasets should be in the same dataset_versions as original"
