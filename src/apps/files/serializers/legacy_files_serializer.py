import logging
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Callable, List, Optional

import requests
from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.utils import timezone
from isodate import parse_datetime
from rest_framework import serializers

from apps.common.helpers import batched
from apps.files.models import File, FileStorage


@dataclass
class FileMigrationCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class LegacyFileSerializer(serializers.Serializer):
    """Serializer for converting V2 file dict to V3 file dict.

    Note: As a side effect, creates required FileStorage instances in the validation step.
    """

    id = serializers.IntegerField()
    file_storage = serializers.DictField()
    project_identifier = serializers.CharField()
    identifier = serializers.CharField()
    file_path = serializers.CharField()
    frozen = serializers.DateTimeField()
    modified = serializers.DateTimeField()
    removed = serializers.DateTimeField()
    checksum = serializers.DictField(required=False)
    byte_size = serializers.IntegerField(required=False)
    user_created = serializers.CharField(required=False)
    is_pas_compatible = serializers.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_cache = {}

    def get_file_storage(self, legacy_file: dict) -> FileStorage:
        """Cache file storages corresponding to legacy storage and project."""
        key = (legacy_file["file_storage"]["identifier"], legacy_file["project_identifier"])
        if key not in self.storage_cache:
            self.storage_cache[key] = FileStorage.get_or_create_from_legacy(legacy_file)
        return self.storage_cache.get(key)

    def to_internal_value(self, data):
        storage = self.get_file_storage(data)
        return File.values_from_legacy(data, storage)


class LegacyFilesSerializer(serializers.ListSerializer):
    """Serializer for saving list of V2 file dicts to V3."""

    child = LegacyFileSerializer()

    update_fields = [
        "record_modified",
        "filename",
        "directory_path",
        "size",
        "checksum",
        "frozen",
        "modified",
        "removed",
        "is_pas_compatible",
        "user",
    ]  # fields that are updated
    diff_fields = set(update_fields) - {"record_modified"}  # fields used for diffing
    date_diff_fields = {"frozen", "modified"}  # date fields used for diffing

    def is_file_changed(self, old_values: dict, new_values: dict):
        """Determine if file has changed values that should be updated."""
        for field in self.diff_fields:
            old_value = old_values.get(field)
            new_value = new_values.get(field)
            if old_value != new_value:
                if field == "removed" and old_value and new_value:
                    continue  # Ignore exact removal dates if both are removed
                if field in self.date_diff_fields and old_value and new_value:
                    if old_value == parse_datetime(new_value):
                        continue
                return True
        return False

    def determine_file_operations(self, legacy_v3_values: dict):
        """Determine file objects to be created or updated."""
        now = timezone.now()
        found_legacy_ids = set()  # Legacy ids of found files
        update = []  # Existing files that need to be updated
        existing_v3_files = File.all_objects.filter(legacy_id__in=legacy_v3_values).values()
        for file in existing_v3_files:
            legacy_id = file["legacy_id"]
            if legacy_file_as_v3 := legacy_v3_values.get(legacy_id):
                found_legacy_ids.add(legacy_id)
                # Update only changed files
                if self.is_file_changed(file, legacy_file_as_v3):
                    # Assign file id and updated values
                    legacy_file_as_v3["id"] = file["id"]
                    legacy_file_as_v3["record_modified"] = now
                    update.append(File(**legacy_file_as_v3))

        create = [
            File(**legacy_file_as_v3)
            for legacy_id, legacy_file_as_v3 in legacy_v3_values.items()
            if legacy_id not in found_legacy_ids
        ]
        return create, update

    def migrate_files(
        self,
        files: List[dict],
        batch_callback: Optional[Callable[[FileMigrationCounts], None]] = FileMigrationCounts,
    ) -> FileMigrationCounts:
        """Create or update list of legacy file dicts."""
        total_counts = FileMigrationCounts()

        if not files:
            return total_counts

        for file_batch in batched(files, 10000):
            legacy_v3_values = {  # Mapping of {legacy_id: v3 dict} for v2 files
                file["legacy_id"]: file for file in file_batch
            }
            create, update = self.determine_file_operations(legacy_v3_values)
            File.all_objects.bulk_create(
                [*create, *update],
                batch_size=10000,
                update_conflicts=True,
                unique_fields=["legacy_id"],
                update_fields=self.update_fields,
            )

            if batch_callback:
                batch_callback(
                    FileMigrationCounts(
                        created=len(create),
                        updated=len(update),
                        unchanged=len(file_batch) - len(create) - len(update),
                    )
                )
            total_counts.created += len(create)
            total_counts.updated += len(update)
            total_counts.unchanged += len(file_batch) - len(create) - len(update)
        return total_counts

    def save(
        self, batch_callback: Optional[Callable[[FileMigrationCounts], None]] = None
    ) -> FileMigrationCounts:
        return self.migrate_files(self.validated_data, batch_callback)
