import pytest
from apps.core.factories import (
    LanguageFactory,
    AccessTypeFactory,
    DatasetActorFactory,
    DatasetFactory,
    ThemeFactory,
    AccessRightsFactory,
    DatasetLicenseFactory,
    ProvenanceFactory,
)
from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.versioning]


def test_create_new_version(language, keyword, dataset):
    DatasetActorFactory.create_batch(2, dataset=dataset)
    ProvenanceFactory(dataset=dataset)
    dataset.language.add(language)
    dataset.theme.add(keyword)
    new_version, old_version = Dataset.create_copy(dataset)
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
    assert old_version.actors.difference(new_version.actors.all()).count() == 2
    assert old_version.provenance.difference(new_version.provenance.all()).count() == 1


def test_edit_new_version(dataset_with_foreign_keys):
    lic = DatasetLicenseFactory()
    dataset_with_foreign_keys.access_rights = AccessRightsFactory()
    dataset_with_foreign_keys.access_rights.license.add(lic)
    new_version, old_version = Dataset.create_copy(dataset_with_foreign_keys)
    new_version.title = {"fi": "New title"}
    new_version.language.add(LanguageFactory())
    new_version.access_rights.access_type = AccessTypeFactory(url="http://example.com")
    new_version.save()
    assert new_version.access_rights.license.all().count() == 1
    assert (
        new_version.access_rights.license.all().first().id
        != old_version.access_rights.license.all().first().id
    )
    assert new_version.language.all().count() != old_version.language.all().count()


def test_publish_dataset(dataset):
    dataset.state = dataset.StateChoices.PUBLISHED
    dataset.save()
    assert dataset.published_revision == 1
    assert dataset.issued is not None
    dataset.save()
    assert dataset.published_revision == 2
    assert dataset.draft_revision == 0
    dataset.state = dataset.StateChoices.DRAFT
    dataset.save()
    assert dataset.published_revision == 2
    assert dataset.draft_revision == 1


def test_latest_published_property(dataset):
    dataset.state = dataset.StateChoices.PUBLISHED
    dataset.save()
    dataset.save()
    assert dataset.latest_published_revision.published_revision == 2


def test_other_versions(dataset):
    dataset.state = dataset.StateChoices.PUBLISHED
    dataset.save()
    second, first = Dataset.create_copy(dataset)
    third, second = Dataset.create_copy(second)
    assert first.other_versions.all().count() == 2
    assert second.other_versions.all().count() == 2
    assert third.other_versions.all().count() == 2
    assert str(third.first_version.id) == str(first.id)
    assert str(first.last_version.id) == str(third.id)
    assert str(first.next_version.id) == str(second.id)
    assert str(third.previous_version.id) == str(second.id)
    assert first.created < second.created < third.created
