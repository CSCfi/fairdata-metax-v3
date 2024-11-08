from typing import Dict, List
from uuid import UUID

from django.apps import apps as django_apps
from django.db import models
from rest_framework import serializers

from apps.common.helpers import is_valid_uuid, merge_sets
from apps.core.models import DatasetVersions
from apps.core.models.legacy import LegacyDataset


class LegacyDatasetVersionSerializer(serializers.Serializer):
    identifier = serializers.UUIDField()


def get_or_create_dataset_versions(legacy_dataset: LegacyDataset) -> DatasetVersions:
    """Get or create DatasetVersions for a LegacyDataset.

    LegacyDataset.dataset_json.dataset_version_set and DataSetVersions.legacy_versions are
    used to determine if an existing DatasetVersions should be used.
    """
    versions_ids = []
    dataset_json = legacy_dataset.dataset_json
    version_set_json = dataset_json.get("dataset_version_set")
    if version_set_json:
        serializer = LegacyDatasetVersionSerializer(data=version_set_json, many=True)
        serializer.is_valid(raise_exception=True)
        versions_ids = [version["identifier"] for version in serializer.validated_data]

    # Add draft relations to id list (V2 omits drafts from dataset_version_set listing)
    for field_name in ["draft_of", "next_draft"]:
        value = (dataset_json.get(field_name) or {}).get("identifier")
        if value and is_valid_uuid(value):
            versions_ids.append(UUID(value))

    # Ensure dataset is in its own legacy_versions
    versions_ids.append(UUID(legacy_dataset.legacy_identifier))

    versions_ids = sorted(set(versions_ids))

    # Does dataset already have dataset_versions?
    dataset_versions = None
    if dataset := legacy_dataset.dataset:
        dataset_versions = dataset.dataset_versions

    # Is dataset mentioned in any LegacyDataset.legacy_versions?
    if not dataset_versions:
        dataset_versions = DatasetVersions.objects.filter(
            legacy_versions__contains=[legacy_dataset.legacy_identifier]
        ).first()

    # Is any DatasetVersions associated with a dataset in dataset_version_set?
    if not dataset_versions:
        dataset_versions = DatasetVersions.objects.filter(datasets__in=versions_ids).first()

    # No existing DatasetVersions found, create new object.
    if not dataset_versions:
        return DatasetVersions.objects.create(legacy_versions=versions_ids)

    # Add missing version identifiers to legacy_versions
    legacy_versions_set = set(dataset_versions.legacy_versions)
    if not legacy_versions_set.issuperset(versions_ids):
        legacy_versions_set.update(versions_ids)
        dataset_versions.legacy_versions = sorted(legacy_versions_set)
        dataset_versions.save()

    return dataset_versions


def _assign_dataset_version(
    version_set: List[UUID],
    version_sets_by_id: Dict[UUID, models.Model],
    datasets_by_id: Dict[UUID, models.Model],
    dataset_updates: List[models.Model],
    new_dataset_versions: List[models.Model],
    versions_model: models.Model,
):
    # Use existing DatasetVersion from a dataset in version_set if possible
    dataset_versions = None
    for identifier in version_set:
        if dataset := datasets_by_id.get(identifier):
            dataset_versions = version_sets_by_id.get(dataset.dataset_versions_id)
            if dataset_versions:
                break

    # Initialize (but don't save yet) new DatasetVersions if needed
    if not dataset_versions:
        dataset_versions = versions_model()
        new_dataset_versions.append(dataset_versions)
        version_sets_by_id[dataset_versions.id] = dataset_versions

    # Assign all datasets to same DatasetVersions
    for identifier in version_set:
        if dataset := datasets_by_id.get(identifier):
            if dataset.dataset_versions_id != dataset_versions.id:
                dataset.dataset_versions_id = dataset_versions.id
                dataset_updates.append(dataset)

    # Assign legacy_versions to DatasetVersions
    dataset_versions.legacy_versions = sorted(version_set)


def migrate_dataset_versions(apps=django_apps):
    """Assign all datasets to DatasetVersions based on legacy data.

    Intended for use in a data migration. Does the following:
    - Assign datasets to same DatasetVersions as other datasets in dataset_json.dataset_version_set
    - Add id of each dataset in dataset_version_set to DatasetVersions.legacy_versions
    """
    versions_model = apps.get_model("core", "DatasetVersions")
    legacy_dataset_model = apps.get_model("core", "LegacyDataset")
    dataset_model = apps.get_model("core", "Dataset")

    # Collect all datasets and version sets by their identifiers
    datasets_by_id = dataset_model.objects.only("id", "dataset_versions_id").in_bulk()
    version_sets_by_id = versions_model.objects.in_bulk()

    # Get all legacy dataset_version_set lists
    legacy_versions_data = legacy_dataset_model.objects.filter(
        dataset_json__dataset_version_set__isnull=False
    ).values(
        identifier=models.F("dataset_json__identifier"),
        next_draft=models.F("dataset_json__next_draft__identifier"),
        draft_of=models.F("dataset_json__draft_of__identifier"),
        version_set=models.F("dataset_json__dataset_version_set"),
    )

    # Collect identifiers, merge all sets containing at least one common dataset
    legacy_version_data_ids = []
    for version_data in legacy_versions_data:
        ids = [UUID(version["identifier"]) for version in version_data["version_set"]]
        # Draft dataset isn't listed in its own version_set in V2
        # so we add the identifier manually just in case
        if identifier := version_data["identifier"]:
            ids.append(UUID(identifier))
        if next_draft := version_data["next_draft"]:
            ids.append(UUID(next_draft))
        if draft_of := version_data["draft_of"]:
            ids.append(UUID(draft_of))
        legacy_version_data_ids.append(ids)
    legacy_version_sets = merge_sets(legacy_version_data_ids)

    dataset_updates = []
    new_version_sets = []
    for version_set in legacy_version_sets:
        _assign_dataset_version(
            version_set=version_set,
            datasets_by_id=datasets_by_id,
            version_sets_by_id=version_sets_by_id,
            new_dataset_versions=new_version_sets,
            dataset_updates=dataset_updates,
            versions_model=versions_model,
        )

    versions_model.objects.bulk_create(new_version_sets)
    versions_model.objects.bulk_update(version_sets_by_id.values(), fields=["legacy_versions"])
    dataset_model.objects.bulk_update(dataset_updates, fields=["dataset_versions_id"])
    versions_model.objects.filter(
        datasets__isnull=True
    ).delete()  # remove versions without datasets
