import pytest

from apps.core.factories import (
    AccessRightsFactory,
    AccessTypeFactory,
    DatasetActorFactory,
    DatasetLicenseFactory,
    LanguageFactory,
    ProvenanceFactory,
)
from apps.core.models import Dataset

pytestmark = [pytest.mark.django_db, pytest.mark.dataset, pytest.mark.versioning]


def test_create_new_version(language, theme, dataset):
    DatasetActorFactory.create_batch(2, dataset=dataset)
    ProvenanceFactory(dataset=dataset)
    dataset.language.add(language)
    dataset.theme.add(theme)
    old_version = dataset
    dataset.publish()
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
    second.persistent_identifier = "doi:5678"
    second.publish()
    third = Dataset.create_new_version(second)
    assert first.dataset_versions == second.dataset_versions == third.dataset_versions
    assert first.version == 1
    assert second.version == 2
    assert third.version == 3
    assert first.next_existing_version.id == second.id
    assert second.next_existing_version.id == third.id
    assert third.next_existing_version == None
    assert first.created < second.created < third.created


def collect_copy_info(model, path="", copy_info=None, ignore_fields=None, model_stack=[]):
    """Determine which fields will be copied or reused when model instance is copied."""
    if model_stack and model_stack[-1] == model:
        return  # prevent infinite org recursion
    model_stack.append(model)

    if not ignore_fields:
        ignore_fields = set()
    if not copy_info:
        copy_info = {}
    all_fields = model._meta.get_fields()
    forward_relation_fields = [f for f in all_fields if f.is_relation and f.concrete]
    reverse_relation_fields = [f for f in all_fields if f.is_relation and not f.concrete]

    for field in forward_relation_fields:
        if field.name in ignore_fields:
            continue
        if field.name in model.copier.parent_relations:
            continue

        new_path = f"{path}.{field.name}"
        if field.name in model.copier.copied_relations:
            copy_info[new_path] = "copy"
            collect_copy_info(
                field.related_model, new_path, copy_info=copy_info, ignore_fields=ignore_fields
            )
        else:
            if (
                field.one_to_one
                and model != field.related_model
                and issubclass(model, field.related_model)
            ):
                continue  # hide e.g. actor_ptr of DatasetActor
            copy_info[new_path] = "existing"

    for field in reverse_relation_fields:
        if field.name in ignore_fields:
            continue
        if field.name in model.copier.parent_relations:  # hide parent relations
            continue

        if field.name in model.copier.copied_relations:
            new_path = f"{path}.{field.name}"
            copy_info[new_path] = "copy"
            collect_copy_info(
                field.related_model, new_path, copy_info=copy_info, ignore_fields=ignore_fields
            )

        if field.name not in model.copier.copied_relations:
            new_path = f"{path}.{field.name}"
            copy_info[new_path] = "omit"

    model_stack.pop()
    return copy_info


def test_dataset_copied_fields():
    copy_info = collect_copy_info(
        Dataset,
        path="dataset",
        ignore_fields={
            "preservation",  # preservation is emptied manually
            "system_creator",  # hide to reduce noise
        },
    )
    copied = {key for key, value in copy_info.items() if value == "copy"}
    existing = {key for key, value in copy_info.items() if value == "existing"}
    omit = {key for key, value in copy_info.items() if value == "omit"}

    # Relations that should use new copies of related objects:
    assert copied == {
        "dataset.access_rights",
        "dataset.access_rights.license",
        "dataset.actors",
        "dataset.actors.organization",
        "dataset.actors.organization.homepage",
        "dataset.actors.organization.parent",
        "dataset.actors.person",
        "dataset.actors.person.homepage",
        "dataset.file_set.directory_metadata",
        "dataset.file_set.file_metadata",
        "dataset.file_set",
        "dataset.other_identifiers",
        "dataset.projects.funding.funder.organization.homepage",
        "dataset.projects.funding.funder.organization.parent",
        "dataset.projects.funding.funder.organization",
        "dataset.projects.funding.funder",
        "dataset.projects.funding",
        "dataset.projects.participating_organizations.homepage",
        "dataset.projects.participating_organizations.parent",
        "dataset.projects.participating_organizations",
        "dataset.projects",
        "dataset.provenance.is_associated_with.organization.homepage",
        "dataset.provenance.is_associated_with.organization.parent",
        "dataset.provenance.is_associated_with.organization",
        "dataset.provenance.is_associated_with.person.homepage",
        "dataset.provenance.is_associated_with.person",
        "dataset.provenance.is_associated_with",
        "dataset.provenance.spatial",
        "dataset.provenance.temporal",
        "dataset.provenance.used_entity",
        "dataset.provenance.variables.concept",
        "dataset.provenance.variables.universe",
        "dataset.provenance.variables",
        "dataset.provenance",
        "dataset.relation.entity",
        "dataset.relation",
        "dataset.remote_resources",
        "dataset.spatial",
        "dataset.temporal",
    }

    # Relations that should reuse the existing objects:
    assert existing == {
        "dataset.access_rights.access_type",
        "dataset.access_rights.license.reference",
        "dataset.access_rights.restriction_grounds",
        "dataset.data_catalog",
        "dataset.dataset_versions",
        "dataset.draft_of",
        "dataset.field_of_science",
        "dataset.file_set.directory_metadata.storage",
        "dataset.file_set.directory_metadata.use_category",
        "dataset.file_set.file_metadata.file_type",
        "dataset.file_set.file_metadata.file",
        "dataset.file_set.file_metadata.use_category",
        "dataset.file_set.files",
        "dataset.file_set.storage",
        "dataset.infrastructure",
        "dataset.language",
        "dataset.last_modified_by",
        "dataset.metadata_owner",
        "dataset.other_identifiers.identifier_type",
        "dataset.permissions",
        "dataset.projects.funding.funder.funder_type",
        "dataset.provenance.event_outcome",
        "dataset.provenance.lifecycle_event",
        "dataset.provenance.preservation_event",
        "dataset.provenance.spatial.reference",
        "dataset.provenance.used_entity.type",
        "dataset.relation.entity.type",
        "dataset.relation.relation_type",
        "dataset.remote_resources.file_type",
        "dataset.remote_resources.use_category",
        "dataset.spatial.reference",
        "dataset.theme",
    }

    # Reverse relations that are not copied:
    # Any parent relations that show up here (e.g. dataset.access_rights.dataset)
    # should be added to corresponding parent_relations list
    # (e.g. AccessRights.copier.parent_relations) to indicate they
    # are intentionally omitted when creating a copy.
    assert omit == {
        "dataset.projects.participating_organizations.children",
        "dataset.legacydataset",
        "dataset.metrics",
        "dataset.provenance.is_associated_with.organization.children",
        "dataset.actors.organization.children",
        "dataset.projects.funding.funder.organization.children",
        "dataset.next_draft",
    }
