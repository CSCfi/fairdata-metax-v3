import logging
from argparse import ArgumentParser
from typing import List

import requests
from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.utils import timezone
from isodate import parse_datetime

from apps.common.helpers import batched
from apps.files.models import File, FileStorage

from ._v2_client import MigrationV2Client

logger = logging.getLogger(__name__)


storage_shorthands = {
    "ida": "urn:nbn:fi:att:file-storage-ida",
    "pas": "urn:nbn:fi:att:file-storage-pas",
}


class Command(BaseCommand):
    """Migrate V2 files to V3 from specific Metax instance

    The script is safe to run multiple times on the same files.
    Only files that have changed are updated.

    !!! Note
    The file id values in legacy Metax are autoincrementing integers
    and will have conflicts across different legacy Metax instances. Files with
    a specific legacy_id will contain values mostly from the latest migration they
    were in, which may produce weird results if multiple legacy Metax instances are
    migrated into the same V3 instance.

    Examples:
        Migrate all files from configured metax instance

            $ python manage.py migrate_v2_files --use-env

        Migrate only files associated with specified V2 datasets

            $ python manage.py migrate_v2_datasets --use-env  \
              --datasets c955e904-e3dd-4d7e-99f1-3fed446f96d1 c955e904-e3dd-4d7e-99f1-3fed446f96d3
    """

    allow_fail = False
    force = False
    created = 0
    updated = 0
    migrated = 0
    ok_after_update = 0
    migration_limit = 0
    compatibility_errors = 0

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_datasets = []
        self.storage_cache = {}
        self.metax_instance = None
        self.metax_user = None
        self.metax_password = None

    def add_arguments(self, parser: ArgumentParser):
        MigrationV2Client.add_arguments(parser)
        parser.add_argument(
            "--datasets",
            nargs="+",
            type=str,
            help="List of Metax V1-V2 dataset identifiers to migrate. "
            "Does not require credentials for open public datasets.",
        )
        parser.add_argument(
            "--datasets-from-catalogs",
            nargs="+",
            type=str,
            help="List of Metax V1-V2 data catalogs to migrate. "
            "Does not require credentials for open public datasets.",
        )
        parser.add_argument(
            "--projects",
            nargs="+",
            type=str,
            help="List of projects to migrate",
        ),
        parser.add_argument(
            "--storages",
            nargs="+",
            type=str,
            help="List of file storages to migrate, e.g. "
            "'urn:nbn:fi:att:file-storage-ida' or short form 'ida'",
        ),
        parser.add_argument(
            "--pagination-size",
            "-ps",
            type=int,
            required=False,
            default=10000,
            help="Number of files to migrate per request",
        )
        parser.add_argument(
            "--allow-fail",
            "-af",
            action="store_true",
            required=False,
            default=False,
            help="Allow individual datasets to fail without halting the migration",
        )

    def print_status_line(self):
        created = self.created
        updated = self.updated
        processed = self.migrated
        fps = processed / (timezone.now() - self.started).total_seconds()
        self.stdout.write(f"{processed=}, {created=:}, {updated=} ({fps:.1f}/s)")

    def get_file_storage(self, legacy_file: dict):
        """Cache file storages corresponding to legacy storage and project."""
        key = (legacy_file["file_storage"]["identifier"], legacy_file["project_identifier"])
        if key not in self.storage_cache:
            self.storage_cache[key] = FileStorage.get_or_create_from_legacy(legacy_file)
        return self.storage_cache.get(key)

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

    def migrate_files(self, files: List[dict]):
        """Create or update list of legacy file dicts."""
        if not files:
            return

        for file_batch in batched(files, 10000):
            legacy_v3_values = {  # Mapping of {legacy_id: v3 dict} for v2 files
                f["id"]: File.values_from_legacy(f, self.get_file_storage(f)) for f in file_batch
            }
            create, update = self.determine_file_operations(legacy_v3_values)
            created = File.all_objects.bulk_create(create, batch_size=2000)
            self.created += len(created)
            updated_count = File.all_objects.bulk_update(
                update, fields=self.update_fields, batch_size=2000
            )
            self.updated += updated_count
            self.migrated += len(file_batch)
            self.print_status_line()

        return None

    def migrate_dataset_files(self, dataset_json: dict):
        identifier = dataset_json["identifier"]
        if self.dataset_may_have_files(dataset_json):
            try:
                files = self.client.fetch_dataset_files(identifier)
                if files:
                    self.migrate_files(files)
            except requests.HTTPError as e:
                self.stderr.write(f"Error for dataset {identifier}: {e.__repr__()}")
                if not self.allow_fail:
                    raise

    def migrate_catalogs_files(self, catalogs):
        for catalog in catalogs:
            catalog = self.client.check_catalog(catalog)
            if not catalog:
                self.stderr.write(f"Invalid catalog identifier: {catalog}")
                continue

            self.stdout.write(f"--- Migrating files for catalog {catalog} ---")
            params = {
                "data_catalog": catalog,
                "limit": 100,
                "fields": "identifier,research_dataset,deprecated,removed",
            }
            datasets = self.client.fetch_datasets(params=params)
            for dataset_json in datasets:
                self.migrate_dataset_files(dataset_json)

    def migrate_projects_files(self, projects, params):
        for project in self.projects:
            params["project_identifier"] = project
            self.stdout.write(f"--- Migrating files for project {project} ---")
            file_batches = self.client.fetch_files(params=params, batched=True)
            for batch in file_batches:
                self.migrate_files(batch)

    def migrate_all_files(self, params):
        self.stdout.write("--- Migrating all files ---")
        file_batches = self.client.fetch_files(params, batched=True)
        for batch in file_batches:
            self.migrate_files(batch)

    def migrate_datasets_files(self, datasets: List[str]):
        for identifier in datasets:
            params = {"fields": "identifier,research_dataset,deprecated,removed"}
            dataset_json = None
            try:
                dataset_json = self.client.fetch_dataset(identifier, params=params)
            except requests.HTTPError as e:
                self.stderr.write(f"Error for dataset {identifier}: {e.__repr__()}")
                if not self.allow_fail:
                    raise
            if dataset_json:
                self.migrate_dataset_files(dataset_json)

    def migrate_from_metax(self, options):
        self.allow_fail = options.get("allow_fail")
        limit = options.get("pagination_size")
        self.force = options.get("force")
        self.migration_limit = options.get("stop_after")

        # Migrating from /rest/v2/datasets/<id>/files,
        # no credentials needed for open datasets
        if self.datasets:
            self.migrate_datasets_files(self.datasets)
            return
        if self.datasets_from_catalogs:
            self.migrate_catalogs_files(self.datasets_from_catalogs)
            return

        # Migrating from /rest/v2/files, credentials are needed
        params = {"limit": limit}
        if self.storages:
            params["file_storage"] = ",".join(self.storages)

        if self.projects:
            self.migrate_projects_files(self.projects, params)
        else:
            self.migrate_all_files(params)

    def dataset_may_have_files(self, dataset_json: dict):
        byte_size = None
        try:
            byte_size = dataset_json["research_dataset"].get("total_files_byte_size")
        except Exception:
            pass
        return bool(byte_size or dataset_json.get("deprecated"))

    def handle(self, *args, **options):
        self.started = timezone.now()
        self.datasets = options.get("datasets") or []
        self.datasets_from_catalogs = options.get("datasets_from_catalogs") or []
        self.projects = options.get("projects") or []
        self.storages = [storage_shorthands.get(s) or s for s in (options.get("storages") or [])]
        self.allow_fail = options.get("allow_fail")
        self.force = options.get("force")
        self.verbosity = options.get("verbosity")  # defaults to 1

        if (self.datasets or self.datasets_from_catalogs) and (self.projects or self.storages):
            self.stderr.write(
                "The projects and storages arguments are not supported with datasets"
            )
            return

        self.client = MigrationV2Client(options, stdout=self.stdout, stderr=self.stderr)
        if not self.client.ok:
            self.stderr.write("Missing Metax V2 configuration")
            return

        try:
            with cachalot_disabled():
                self.migrate_from_metax(options)
        except KeyboardInterrupt:
            pass
