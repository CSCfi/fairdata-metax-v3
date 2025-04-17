import pytest
from django.db import transaction

from apps.common.profiling import count_queries
from apps.core.factories import PublishedDatasetFactory
from apps.core.models import Dataset, Provenance, Spatial, Temporal

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def collect_copy_info(model, path="", copy_info=None, ignore_fields=None, model_stack=None):
    """Determine which fields will be copied or reused when model instance is copied."""
    if model_stack is None:
        model_stack = []
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
                field.related_model,
                new_path,
                copy_info=copy_info,
                ignore_fields=ignore_fields,
                model_stack=model_stack,
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
                field.related_model,
                new_path,
                copy_info=copy_info,
                ignore_fields=ignore_fields,
                model_stack=model_stack,
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
        "dataset.custom_rems_licenses",
        "dataset.legacydataset",
        "dataset.metrics",
        "dataset.provenance.is_associated_with.organization.children",
        "dataset.actors.organization.children",
        "dataset.projects.funding.funder.organization.children",
        "dataset.next_draft",
        "dataset.sync_status",
    }


def test_dataset_copy_bulk():
    """Test that nested objects are copied using bulk_create."""
    orig: Dataset = PublishedDatasetFactory()

    spatials = []
    temporals = []
    provenances = []
    provenance_spatials = []
    for i in range(5):
        spatials.append(Spatial(geographic_name=f"spatial-{i}"))
        temporals.append(Temporal(temporal_coverage=f"time {i}"))

    for i in range(10):
        spatial = Spatial(geographic_name=f"provenance-spatial-{i}")
        provenance_spatials.append(spatial)
        provenances.append(Provenance(title={"en": f"provenance-{i}"}, spatial=spatial))

    Spatial.objects.bulk_create(spatials + provenance_spatials)
    Provenance.objects.bulk_create(provenances)
    Temporal.objects.bulk_create(temporals)
    orig.spatial.set(spatials)
    orig.provenance.set(provenances)
    orig.temporal.set(temporals)

    with count_queries() as count:
        with transaction.atomic():
            copy = orig.create_copy()

    # Copying dataset should copy spatials, provenances and temporals
    # in one insert per model instead of saving instances one-by-one
    assert count["SQLInsertCompiler"]["Spatial"] == 1
    assert count["SQLInsertCompiler"]["Provenance"] == 1
    assert count["SQLInsertCompiler"]["Temporal"] == 1

    # Check that values are actually copied
    assert Spatial.objects.count() == 15 * 2
    assert Provenance.objects.count() == 10 * 2
    assert Temporal.objects.count() == 5 * 2

    assert list(orig.spatial.values("geographic_name")) == list(
        copy.spatial.values("geographic_name")
    )
    orig_spatial_ids = set(orig.spatial.values_list("id", flat=True))
    copy_spatial_ids = set(copy.spatial.values_list("id", flat=True))
    assert orig_spatial_ids.isdisjoint(copy_spatial_ids)

    assert list(orig.provenance.values("title", "spatial__geographic_name")) == list(
        copy.provenance.values("title", "spatial__geographic_name")
    )
    orig_provenance_ids = set(orig.provenance.values_list("id", flat=True))
    copy_provenance_ids = set(copy.provenance.values_list("id", flat=True))
    assert orig_provenance_ids.isdisjoint(copy_provenance_ids)

    orig_provenance_spatial_ids = set(orig.provenance.values_list("spatial_id", flat=True))
    copy_provenance_spatial_ids = set(copy.provenance.values_list("spatial_id", flat=True))
    assert orig_provenance_spatial_ids.isdisjoint(copy_provenance_spatial_ids)

    assert list(orig.temporal.values("temporal_coverage")) == list(
        copy.temporal.values("temporal_coverage")
    )
    orig_temporal_ids = set(orig.temporal.values_list("id", flat=True))
    copy_temporal_ids = set(copy.temporal.values_list("id", flat=True))
    assert orig_temporal_ids.isdisjoint(copy_temporal_ids)
