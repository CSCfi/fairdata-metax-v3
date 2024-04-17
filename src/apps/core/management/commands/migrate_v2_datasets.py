import copy
import json
import logging
import uuid
from argparse import ArgumentParser
from typing import Optional

import requests
from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.db.models import Q
from isodate import parse_datetime

from apps.common.helpers import is_valid_uuid, parse_iso_dates_in_nested_dict
from apps.core.models import LegacyDataset

logger = logging.getLogger(__name__)


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
    dataset_cache = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_datasets = []
        self.datasets = []
        self.dataset_cache = {}

    def add_arguments(self, parser: ArgumentParser):
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
            "--metax-instance",
            "-mi",
            type=str,
            required=False,
            default="http://localhost:8002",
            help="Fully qualified Metax instance URL to migrate datasets from",
        )
        parser.add_argument(
            "--pagination_size",
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

    def get_v3_version(self, dataset: LegacyDataset):
        if v3_version := getattr(dataset, "_v3_version", None):
            return v3_version

        dataset._v3_version = parse_iso_dates_in_nested_dict(
            copy.deepcopy(dataset.as_v2_dataset())
        )
        return dataset._v3_version

    def get_update_reason(self, dataset: LegacyDataset, dataset_json, created) -> Optional[str]:
        """Get reason, why dataset is migrated again, or None if no update is needed."""
        if created:
            return "created"

        if dataset.migration_errors or not dataset.last_successful_migration:
            return "migration-errors"

        modified = parse_datetime(
            dataset_json.get("date_modified") or dataset_json.get("date_created")
        )
        if modified > dataset.last_successful_migration:
            return "modified"

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

    def migrate_dataset(self, data: dict):
        identifier = data["identifier"]

        if not is_valid_uuid(identifier):
            self.stderr.write(f"Invalid identifier '{identifier}', ignoring")
            return None

        try:
            self.migrated += 1
            ignored = None
            fixed = None
            errors = None
            created = False
            dataset = self.dataset_cache.get(identifier)
            if not dataset:
                dataset, created = LegacyDataset.objects.get_or_create(
                    id=identifier,
                    defaults={"dataset_json": data},
                )
            update_reason = self.get_update_reason(dataset, dataset_json=data, created=created)

            if update_reason:
                if dataset.api_version > 2:
                    self.stdout.write(
                        f"{self.migrated} Dataset '{identifier}' has been modified in V3, not updating"
                    )
                    return None

                self.updated += 1
                dataset.dataset_json = data
                dataset.update_from_legacy(raise_serializer_errors=False)
                fixed = dataset.fixed_legacy_values
                ignored = dataset.invalid_legacy_values
                errors = dataset.migration_errors
                if not errors:
                    self.ok_after_update += 1

            self.print_status_line(dataset, update_reason)
            self.print_fixed(fixed)
            self.print_ignored(ignored)
            self.print_errors(identifier, errors)

            if errors:
                if not self.allow_fail:
                    raise ValueError(errors)
                self.failed_datasets.append(identifier)
            else:
                self.datasets.append(identifier)

            return dataset
        except Exception as e:
            if self.allow_fail:
                self.stderr.write(repr(e))
                self.stderr.write(f"Exception migrating dataset {data['identifier']}\n\n")
                _message = f"{data['identifier']} : {e}"
                self.failed_datasets.append(identifier)
                return None
            else:
                logger.error(f"Failed while processing {identifier}")
                raise e

    def cache_existing_datasets(self, list_json):
        """Get datasets in bulk and assign to dataset_cache."""
        with cachalot_disabled():
            datasets = LegacyDataset.all_objects.in_bulk(
                [ide for d in list_json if is_valid_uuid(ide := d["identifier"])]
            )
        self.dataset_cache = {str(k): v for k, v in datasets.items()}

    def migrate_from_list(self, list_json):
        self.cache_existing_datasets(list_json)
        created_instances = []
        for data in list_json:
            if self.update_limit != 0 and self.updated >= self.update_limit:
                break
            dataset = self.migrate_dataset(data)
            if dataset:
                created_instances.append(dataset)
        return created_instances

    def loop_pagination(self, response):
        response_json = response.json()
        self.datasets.extend(self.migrate_from_list(response_json["results"]))
        while next_url := response_json.get("next"):
            if self.update_limit != 0 and self.updated >= self.update_limit:
                break
            response = requests.get(next_url)
            response_json = response.json()
            self.datasets.extend(self.migrate_from_list(response_json["results"]))

    def update(self, options):
        q = Q()
        if identifiers := options.get("identifiers"):
            q = Q(id__in=identifiers)
        if catalogs := options.get("catalogs"):
            q = Q(data_catalog__in=catalogs)
        datasets = LegacyDataset.available_objects.filter(q).values_list("dataset_json", flat=True)
        self.migrate_from_list(datasets)

    def migrate_from_file(self, options):
        file = options.get("file")
        identifiers = set(options.get("identifiers") or [])
        catalogs = options.get("catalogs")
        datasets = []
        with open(file) as f:
            datasets = json.load(f)
            if isinstance(datasets, dict):
                datasets = []
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
        metax_instance = options.get("metax_instance")
        self.allow_fail = options.get("allow_fail")
        limit = options.get("pagination_size")
        self.force = options.get("force")
        self.migration_limit = options.get("stop_after")

        if identifiers:
            for identifier in identifiers:
                response = requests.get(f"{metax_instance}/rest/v2/datasets/{identifier}")
                dataset_json = response.json()
                self.datasets.append(self.migrate_dataset(dataset_json))

        if migrate_all:
            response = requests.get(
                f"{metax_instance}/rest/v2/datasets?limit={limit}&include_legacy=true"
            )
            self.loop_pagination(response)

        if catalogs:
            for catalog in catalogs:
                if self.migration_limit != 0 and self.migration_limit <= self.migrated:
                    break
                self.stdout.write(f"Migrating catalog: {catalog}")
                response = requests.get(f"{metax_instance}/rest/datacatalogs/{catalog}")
                if response.status_code == 200:
                    response_json = response.json()
                    _catalog = response_json["catalog_json"]["identifier"]
                else:
                    self.stderr.write(f"Invalid catalog identifier: {catalog}")
                    continue

                response = requests.get(
                    f"{metax_instance}/rest/v2/datasets?data_catalog={_catalog}&limit={limit}&include_legacy=true"
                )
                self.loop_pagination(response)

    def print_summary(self):
        not_ok = self.updated - self.ok_after_update
        self.stdout.write(f"Processed {self.migrated} datasets")
        self.stdout.write(f"- {self.ok_after_update} datasets updated succesfully")
        self.stdout.write(f"- {not_ok} datasets failed")

    def handle(self, *args, **options):
        identifiers = options.get("identifiers")
        update = options.get("update")
        file = options.get("file")
        catalogs = options.get("catalogs")
        self.allow_fail = options.get("allow_fail")
        self.force = options.get("force")
        self.update_limit = options.get("stop_after")
        self.verbosity = options.get("verbosity")  # defaults to 1

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
                self.migrate_from_metax(options)
        except KeyboardInterrupt:
            pass  # Print summary after Ctrl+C

        self.print_summary()
