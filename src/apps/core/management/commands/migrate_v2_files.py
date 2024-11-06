import logging
from argparse import ArgumentParser
from typing import List, Optional

import requests
from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.files.serializers.legacy_files_serializer import (
    FileMigrationCounts,
    LegacyFilesSerializer,
)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_datasets = []
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
        parser.add_argument(
            "--modified-since",
            type=str,
            required=False,
            default=False,
            help="Migrate only files modified since datetime (in ISO 8601 format).",
        )
        parser.add_argument(
            "--file-offset",
            type=int,
            required=False,
            default=0,
            help=(
                "Add offset to file ids and prefix projects and file identifiers."
                "Used for testing migrations from different V2 instances."
            ),
        )

    def print_status_line(self):
        created = self.created
        updated = self.updated
        processed = self.migrated
        fps = processed / (timezone.now() - self.started).total_seconds()
        self.stdout.write(f"{processed=}, {created=:}, {updated=} ({fps:.1f}/s)")

    def offset_files(self, files: List[dict], offset: int):
        if not offset:
            return
        for file in files:
            file["id"] += offset
            file["identifier"] = f'{offset}-{file["identifier"]}'
            file["project_identifier"] = f'{offset}-{file["project_identifier"]}'

    def migrate_files(self, files: List[dict]):
        """Create or update list of legacy file dicts."""
        if not files:
            return

        self.offset_files(files, self.file_offset)

        def callback(counts: FileMigrationCounts):
            self.created += counts.created
            self.updated += counts.updated
            self.migrated += counts.created + counts.updated + counts.unchanged
            self.print_status_line()

        serializer = LegacyFilesSerializer(data=files)
        serializer.is_valid(raise_exception=True)
        serializer.save(batch_callback=callback)
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
            file_batches = self.client.fetch_files(
                params=params, batched=True, modified_since=self.modified_since
            )
            for batch in file_batches:
                self.migrate_files(batch)

    def migrate_all_files(self, params):
        if self.modified_since:
            self.stdout.write(f"--- Migrating files modified since {self.modified_since} ---")
        else:
            self.stdout.write("--- Migrating all files ---")
        file_batches = self.client.fetch_files(
            params, batched=True, modified_since=self.modified_since
        )
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

    def parse_datetime(self, datetime_str: Optional[str]):
        if not datetime_str:
            return None
        parsed = parse_datetime(datetime_str)
        if not parsed:
            raise ValueError(f"Invalid datetime: {datetime_str}")
        return parsed

    def handle(self, *args, **options):
        self.started = timezone.now()
        self.datasets = options.get("datasets") or []
        self.datasets_from_catalogs = options.get("datasets_from_catalogs") or []
        self.projects = options.get("projects") or []
        self.storages = [storage_shorthands.get(s) or s for s in (options.get("storages") or [])]
        self.allow_fail = options.get("allow_fail")
        self.force = options.get("force")
        self.verbosity = options.get("verbosity")  # defaults to 1
        self.file_offset = options.get("file_offset")
        try:
            self.modified_since = self.parse_datetime(options.get("modified_since"))
        except ValueError as e:
            self.stderr.write(str(e))
            return

        if (self.datasets or self.datasets_from_catalogs) and (
            self.projects or self.storages or self.modified_since
        ):
            self.stderr.write(
                "The projects, storages, and modified-since arguments are not supported with datasets"
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
