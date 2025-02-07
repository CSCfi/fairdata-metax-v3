import copy
import json
import logging
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

import requests
from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.db.models import Q
from isodate import parse_datetime

from apps.common.helpers import is_valid_uuid, parse_iso_dates_in_nested_dict
from apps.core.models import LegacyDataset

from ._v2_client import MigrationV2Client

logger = logging.getLogger(__name__)


@dataclass
class MigrationData:
    identifier: str
    dataset_json: dict
    # When file_ids is None, existing file_ids is used when updating
    # When file_ids is callable, it is called when updating dataset
    file_ids: Optional[Union[dict, Callable]] = None

    def get_file_ids(self):
        if callable(self.file_ids):
            self.file_ids = self.file_ids()
        return self.file_ids

    def offset_files(self, offset: int):
        if not offset:
            return
        rd = self.dataset_json.get("research_dataset", {})
        for file in rd.get("files") or []:
            file["identifier"] = f'{offset}-{file["identifier"]}'
            details = file.get("details")
            if details:
                if details.get("id") is not None:
                    details["id"] += offset
                if details.get("identifier") is not None:
                    details["identifier"] = f'{offset}-{details["identifier"]}'

        for directory in rd.get("directories") or []:
            directory["identifier"] = f'{offset}-{directory["identifier"]}'

        self.file_ids = [fid + offset for fid in self.get_file_ids()]


class Command(BaseCommand):
    """Migrate V2 datasets to V3 from specific Metax instance

    Examples:
        Migrate all publicly available datasets from metax instance

            $ python manage.py migrate_v2_datasets -mi https://metax.fairdata.fi

        Migrate only specified V2 datasets

            $ python manage.py migrate_v2_datasets -ids c955e904-e3dd-4d7e-99f1-3fed446f96d1 c955e904-e3dd-4d7e-99f1-3fed446f96d3 -mi https://metax.fairdata.fi
    """

    allow_fail = False
    failed_datasets = []
    datasets = []
    force = False
    updated = 0
    migrated = 0
    ok_after_update = 0
    migration_limit = 0
    compatibility_errors = 0
    dataset_cache: Dict[str, LegacyDataset] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_datasets = []
        self.dataset_cache = {}
        self.dataset_fetch_errors = 0
        self.dataset_files_fetch_errors = 0

    def add_arguments(self, parser: ArgumentParser):
        MigrationV2Client.add_arguments(parser)
        parser.add_argument(
            "--identifiers",
            "-ids",
            nargs="+",
            type=str,
            help="List of Metax V1-V2 identifiers to migrate",
        )
        parser.add_argument(
            "--catalogs",
            "-c",
            nargs="+",
            type=str,
            help="List of Metax V1-V2 catalogs to migrate",
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
            "--file",
            type=str,
            required=False,
            help="Migrate datasets from JSON file instead of a metax instance",
        ),
        parser.add_argument(
            "--update",
            action="store_true",
            required=False,
            default=False,
            help="Run migration using existing migrated datasets as data source.",
        ),
        parser.add_argument(
            "--pagination-size",
            "-ps",
            type=int,
            required=False,
            default=100,
            help="Number of datasets to migrate per request",
        )
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            required=False,
            default=False,
            help="Update previously migrated datasets even if they have no errors and haven't changed",
        )
        parser.add_argument(
            "--stop-after",
            "-sa",
            type=int,
            required=False,
            default=0,
            help="Stop after updating this many datasets",
        )
        # File ids are not unique across different V2 instances so
        # they need an offset when migrating data from multiple V2
        # instances to avoid conflicts. Also project_identifiers
        # and file identifiers need to be prefixed in case they
        # overlap between different instance.
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

    @property
    def common_dataset_fetch_params(self):
        return {
            "include_user_metadata": "true",  # include dataset-specific file/directory metadata
            "file_details": "true",  # include files[].details and directories[].details
            "file_fields": "id,identifier,file_path",  # fields in files[].details
            "directory_fields": "id,identifier,directory_path",  # fields in directories[].details
        }

    def get_v3_version(self, dataset: LegacyDataset):
        if v3_version := getattr(dataset, "_v3_version", None):
            return v3_version

        dataset._v3_version = parse_iso_dates_in_nested_dict(
            copy.deepcopy(dataset.as_v2_dataset())
        )
        return dataset._v3_version

    def get_update_reason(
        self, legacy_dataset: LegacyDataset, dataset_json, created
    ) -> Optional[str]:
        """Get reason, why dataset is migrated again, or None if no update is needed."""
        if created:
            return "created"

        if legacy_dataset.migration_errors or not legacy_dataset.last_successful_migration:
            return "migration-errors"

        modified = parse_datetime(
            dataset_json.get("date_modified") or dataset_json.get("date_created")
        )
        if modified > legacy_dataset.last_successful_migration:
            return "modified"

        has_files = dataset_json["research_dataset"].get(
            "total_files_byte_size"
        ) or dataset_json.get("deprecated")
        dataset = legacy_dataset.dataset
        if has_files and dataset and not hasattr(dataset, "file_set"):
            # Dataset should have files but does not have file_set, so some are definitely missing
            return "missing-files"

        if self.force:
            return "force"
        return None

    def group_consecutive_same_value(self, d: dict):
        """Helper for grouping identical consecutive values in dict.

        Like dict.items() but returns third value in the tuple
        that is True if the next value is identical to current one.
        """
        prev_key = None
        prev_value = None
        for key, value in d.items():
            if prev_key:
                yield prev_key, value, prev_value == value
            prev_key = key
            prev_value = value
        if prev_key:
            yield prev_key, prev_value, False

    def print_fixed(self, fixed):
        if fixed:
            self.stdout.write("Fixed legacy data:")
            for path, fix, next_is_same in self.group_consecutive_same_value(fixed):
                self.stdout.write(f"- {path}")
                if next_is_same:
                    continue
                self.stdout.write(f"   error: {fix['error']}")
                self.stdout.write(f"   value: {fix['value']}")
                if f := fix.get("fixed_value"):
                    self.stdout.write(f"   fixed: {f}")
                if fields := fix.get("fields"):
                    self.stdout.write(f"   fields: {fields}")

    def print_ignored(self, ignored):
        if ignored:
            self.stdout.write("Ignored invalid legacy data:")
            for path, ign, next_is_same in self.group_consecutive_same_value(ignored):
                self.stdout.write(f"- {path}")
                if next_is_same:
                    continue
                self.stdout.write(f"   value: {ign['value']}")
                self.stdout.write(f"   error: {ign['error']}")
                if fields := ign.get("fields"):
                    self.stdout.write(f"   fields: {fields}")

    def print_errors(self, identifier: str, errors: dict):
        if errors:
            self.stderr.write(f"Errors for dataset {identifier}:")
            for err_type, values in errors.items():
                self.stderr.write(f"- {err_type}")
                for e in values:
                    self.stderr.write(f"   {e}")
            self.stderr.write("")

    def print_status_line(self, dataset, update_reason):
        if update_reason or self.verbosity > 1:
            not_ok = self.updated - self.ok_after_update
            identifier = str(dataset.id)
            failed = ""
            if self.allow_fail:
                failed = f", {not_ok} failed"
            created_objects = dict(dataset.created_objects)
            self.stdout.write(
                f"{self.migrated} ({self.ok_after_update} updated{failed}): {identifier=}, {update_reason=}, {created_objects=}"
            )

    def pre_migrate_checks(self, data: MigrationData) -> bool:
        identifier = data.identifier
        dataset_json = data.dataset_json
        if not is_valid_uuid(identifier):
            self.stderr.write(f"Invalid identifier '{identifier}', ignoring")
            return False

        if dataset_json.get("api_meta", {}).get("version") >= 3:
            self.stdout.write(f"Dataset '{identifier}' is from a later Metax version, ignoring")
            return False

        return True

    def get_data_file_ids(self, data: MigrationData):
        try:
            return data.get_file_ids()
        except Exception:
            self.dataset_files_fetch_errors += 1
            raise

    def update_legacy_dataset(self, data: MigrationData):
        identifier = data.identifier
        dataset_json = data.dataset_json
        ignored = None
        fixed = None
        created = False
        errors = None
        legacy_dataset = self.dataset_cache.get(identifier)
        if not legacy_dataset:
            legacy_dataset, created = LegacyDataset.all_objects.get_or_create(
                id=identifier,
                defaults={
                    "dataset_json": dataset_json,
                    "legacy_file_ids": self.get_data_file_ids(data),
                },
            )

        update_reason = self.get_update_reason(
            legacy_dataset, dataset_json=dataset_json, created=created
        )

        if update_reason and legacy_dataset.dataset and legacy_dataset.dataset.api_version > 2:
            self.stdout.write(
                f"{self.migrated} Dataset '{identifier}' has been modified in V3, not updating"
            )
            return

        if update_reason:
            legacy_dataset.dataset_json = dataset_json
            data.offset_files(self.file_offset)
            legacy_dataset.legacy_file_ids = self.get_data_file_ids(data)
            if not created and legacy_dataset.tracker.changed():
                legacy_dataset.save()

            self.updated += 1
            legacy_dataset.update_from_legacy(raise_serializer_errors=False)
            fixed = legacy_dataset.fixed_legacy_values
            ignored = legacy_dataset.invalid_legacy_values
            errors = legacy_dataset.migration_errors
            if not errors:
                self.ok_after_update += 1

        self.print_status_line(legacy_dataset, update_reason)
        self.print_fixed(fixed)
        self.print_ignored(ignored)
        self.print_errors(identifier, errors)
        return errors

    def migrate_dataset(self, data: MigrationData):
        identifier = data.identifier
        if not self.pre_migrate_checks(data):
            return None

        try:
            self.migrated += 1
            if errors := self.update_legacy_dataset(data):
                if not self.allow_fail:
                    raise ValueError(errors)
                self.failed_datasets.append(identifier)

        except Exception as e:
            if self.allow_fail:
                self.stderr.write(repr(e))
                self.stderr.write(f"Exception migrating dataset {identifier}\n\n")
                self.failed_datasets.append(identifier)
                return None
            else:
                logger.error(f"Failed while processing {identifier}")
                raise

    def cache_existing_datasets(self, data_list: List[MigrationData]):
        """Get datasets in bulk and assign to dataset_cache."""
        with cachalot_disabled():
            datasets = LegacyDataset.all_objects.defer("legacy_file_ids").in_bulk(
                [ide for d in data_list if is_valid_uuid(ide := d.identifier)]
            )
        self.dataset_cache = {str(k): v for k, v in datasets.items()}

    def migrate_from_list(self, data_list: List[MigrationData]):
        self.cache_existing_datasets(data_list)
        for data in data_list:
            if self.update_limit != 0 and self.updated >= self.update_limit:
                break
            self.migrate_dataset(data)

    def migrate_from_json_list(self, dataset_json_list: list, request_files=False):
        data_list = [self.dataset_json_to_data(dataset_json) for dataset_json in dataset_json_list]
        if request_files:
            for item in data_list:
                self.add_dataset_files_callable(item)
        self.migrate_from_list(data_list)

    def update(self, options):
        q = Q()
        if identifiers := options.get("identifiers"):
            q = Q(id__in=identifiers)
        if catalogs := options.get("catalogs"):
            q = Q(dataset__data_catalog__in=catalogs)
        dataset_json_list = LegacyDataset.all_objects.filter(q).values_list(
            "dataset_json", flat=True
        )
        self.migrate_from_json_list(dataset_json_list)

    def dataset_json_to_data(self, dataset_json: dict) -> MigrationData:
        return MigrationData(identifier=dataset_json["identifier"], dataset_json=dataset_json)

    def file_dataset_to_data(self, file_dataset: dict) -> MigrationData:
        # File containing MigrationData dicts
        if dataset_json := file_dataset.get("dataset_json"):
            return MigrationData(
                identifier=file_dataset["identifier"],
                dataset_json=dataset_json,
                file_ids=file_dataset.get("files"),
            )
        # File containing dataset_json dicts
        return self.dataset_json_to_data(file_dataset)

    def migrate_from_file(self, options):
        file = options.get("file")
        identifiers = set(options.get("identifiers") or [])
        catalogs = options.get("catalogs")
        datasets = []

        with open(file) as f:
            datasets = json.load(f)
            if isinstance(datasets, dict):
                datasets = [self.file_dataset_to_data(datasets)]  # single dataset
            else:
                datasets = [self.file_dataset_to_data(d) for d in datasets]
            if identifiers:
                datasets = [d for d in datasets if d.get("identifier") in identifiers]
            if catalogs:
                datasets = [
                    d for d in datasets if d.get("data_catalog", {}).get("identifier") in catalogs
                ]
        self.migrate_from_list(datasets)

    def migrate_from_metax(self, options):
        identifiers = options.get("identifiers")
        catalogs = options.get("catalogs")
        migrate_all = not (catalogs or identifiers)
        self.allow_fail = options.get("allow_fail")
        limit = options.get("pagination_size")
        self.force = options.get("force")
        self.migration_limit = options.get("stop_after")

        if identifiers:
            for identifier in identifiers:
                try:
                    dataset_json = self.client.fetch_dataset(
                        identifier, params=self.common_dataset_fetch_params
                    )
                    data = self.dataset_json_to_data(dataset_json)
                    self.add_dataset_files_callable(data)
                    self.migrate_dataset(data)
                except requests.HTTPError as err:
                    self.dataset_fetch_errors += 1
                    if self.allow_fail:
                        self.stderr.write(str(err))
                    else:
                        raise

        if migrate_all:
            params = {**self.common_dataset_fetch_params, "limit": limit}
            dataset_batches = self.client.fetch_datasets(params, batched=True)
            for batch in dataset_batches:
                self.migrate_from_json_list(batch, request_files=True)

        if catalogs:
            for catalog in catalogs:
                if self.migration_limit != 0 and self.migration_limit <= self.migrated:
                    break

                self.stdout.write(f"Migrating catalog: {catalog}")
                _catalog = self.client.check_catalog(catalog)
                if not _catalog:
                    self.stderr.write(f"Invalid catalog identifier: {catalog}")
                    continue

                params = {
                    **self.common_dataset_fetch_params,
                    "data_catalog": _catalog,
                    "limit": limit,
                }
                dataset_batches = self.client.fetch_datasets(params, batched=True)
                for batch in dataset_batches:
                    self.migrate_from_json_list(batch, request_files=True)

    def print_summary(self):
        not_ok = (
            self.updated
            - self.ok_after_update
            + self.dataset_fetch_errors
            + self.dataset_files_fetch_errors
        )
        self.stdout.write(f"Processed {self.migrated} datasets")
        self.stdout.write(f"- {self.ok_after_update} datasets updated succesfully")
        self.stdout.write(f"- {not_ok} datasets failed")

    def dataset_may_have_files(self, dataset_json: dict) -> bool:
        has_byte_size = None
        try:
            has_byte_size = "total_files_byte_size" in dataset_json["research_dataset"]
        except Exception:
            pass
        return bool(has_byte_size or dataset_json.get("deprecated"))

    def add_dataset_files_callable(self, data: MigrationData):
        """Fetch dataset files lazily when needed using callable."""
        if self.dataset_may_have_files(data.dataset_json):
            data.file_ids = lambda: self.client.fetch_dataset_file_ids(data.identifier)
        else:
            data.file_ids = []
        return data

    def handle(self, *args, **options):
        identifiers = options.get("identifiers")
        update = options.get("update")
        file = options.get("file")
        catalogs = options.get("catalogs")
        self.allow_fail = options.get("allow_fail")
        self.force = options.get("force")
        self.update_limit = options.get("stop_after")
        self.verbosity = options.get("verbosity")  # defaults to 1
        self.file_offset = options.get("file_offset")

        if bool(update) + bool(file) > 1:
            self.stderr.write("The --file and --update options are mutually exclusive.")
            return

        if bool(identifiers) + bool(catalogs) > 1:
            self.stderr.write("The --identifiers and --catalogs options are mutually exclusive.")
            return

        try:
            if update:
                self.update(options)
            elif file:
                self.migrate_from_file(options)
            else:
                self.client = MigrationV2Client(options, stdout=self.stdout, stderr=self.stderr)
                if not self.client.ok:
                    self.stderr.write("Missing Metax V2 configuration")
                    return
                self.migrate_from_metax(options)
        except KeyboardInterrupt:
            pass  # Print summary after Ctrl+C

        self.print_summary()
