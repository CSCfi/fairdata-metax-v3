from argparse import ArgumentParser
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.exceptions import TopLevelValidationError
from apps.core.models import DataCatalog, Dataset
from apps.core.models.catalog_record.related import RemoteResource
from apps.core.models.data_services import DataService


class Command(BaseCommand):
    help = "Move datasets to another data catalog after validating compatibility."

    DAAS_CATALOG_ID = "urn:nbn:fi:att:data-catalog-daas"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--datasets",
            nargs="+",
            required=True,
            help="List of dataset UUIDs to move.",
        )
        parser.add_argument(
            "--target",
            required=True,
            help="Target data catalog id.",
        )
        parser.add_argument(
            "--dry",
            action="store_true",
            default=False,
            help="Validate only, do not transfer datasets.",
        )

    def _parse_error(self, error: Exception) -> Any:
        if isinstance(error, DRFValidationError):
            return error.detail
        if isinstance(error, TopLevelValidationError):
            return error.detail
        if hasattr(error, "message_dict"):
            return getattr(error, "message_dict")
        if hasattr(error, "messages"):
            return getattr(error, "messages")
        return str(error)

    def _validate_dataset(self, dataset: Dataset, target: DataCatalog) -> dict:
        errors = {}
        old_catalog = dataset.data_catalog
        old_catalog_id = dataset.data_catalog_id
        try:
            dataset.data_catalog = target
            dataset.data_catalog_id = target.id

            try:
                dataset.validate_catalog()
            except Exception as error:
                errors["catalog"] = self._parse_error(error)

            try:
                dataset.validate_unique_fields()
            except Exception as error:
                errors["unique"] = self._parse_error(error)

            if dataset.state == Dataset.StateChoices.PUBLISHED:
                try:
                    dataset.validate_published(require_pid=bool(dataset.persistent_identifier))
                except Exception as error:
                    errors["published"] = self._parse_error(error)

            if hasattr(dataset, "file_set") and dataset.remote_resources.exists():
                errors["files_remote_resources"] = (
                    "Dataset cannot have files and remote resources simultaneously."
                )

            remote_resources = dataset.remote_resources.all()
            invalid_service = remote_resources.filter(data_service__isnull=False).exclude(
                data_service__catalog=target
            )
            if invalid_service.exists():
                errors["remote_resources_data_service"] = (
                    "One or more remote resources reference a data_service that does not belong "
                    "to the target catalog."
                )

            if target.id == self.DAAS_CATALOG_ID and remote_resources.filter(
                data_service__isnull=True
            ).exists():
                other_service = DataService.objects.filter(
                    id="other", catalog_id=self.DAAS_CATALOG_ID
                ).first()
                if not other_service:
                    errors["remote_resources_data_service_required"] = (
                        "Remote resources in DAAS catalog require data_service, "
                        "but the 'other' fallback data service was not found."
                    )
        finally:
            dataset.data_catalog = old_catalog
            dataset.data_catalog_id = old_catalog_id

        return errors

    def _format_validation_errors(self, validation_errors: dict) -> str:
        lines = ["Validation failed for one or more datasets:"]
        for dataset_id, errors in validation_errors.items():
            lines.append(f"- {dataset_id}")
            for key, value in errors.items():
                lines.append(f"  - {key}: {value}")
        return "\n".join(lines)

    def handle(self, *args, **options):
        dataset_ids_raw = options["datasets"]
        target_id = options["target"]
        dry_run = options["dry"]

        target = DataCatalog.objects.filter(id=target_id).first()
        if not target:
            raise CommandError(f"Target data catalog '{target_id}' not found.")

        invalid_ids = []
        dataset_ids = []
        for dataset_id in dataset_ids_raw:
            try:
                dataset_ids.append(UUID(dataset_id))
            except (TypeError, ValueError):
                invalid_ids.append(dataset_id)

        if invalid_ids:
            raise CommandError(f"Invalid dataset UUIDs: {', '.join(invalid_ids)}")

        datasets_by_id = Dataset.all_objects.select_related("data_catalog").in_bulk(dataset_ids)
        missing_ids = [str(dataset_id) for dataset_id in dataset_ids if dataset_id not in datasets_by_id]
        if missing_ids:
            raise CommandError(f"Datasets not found: {', '.join(missing_ids)}")

        datasets = [datasets_by_id[dataset_id] for dataset_id in dataset_ids]
        validation_errors = {}
        for dataset in datasets:
            if dataset.data_catalog_id == target.id:
                continue
            errors = self._validate_dataset(dataset, target)
            if errors:
                validation_errors[str(dataset.id)] = errors

        if validation_errors:
            raise CommandError(self._format_validation_errors(validation_errors))

        if dry_run:
            self.stdout.write(f"Dry run successful. Validated {len(datasets)} datasets.")
            return

        now = timezone.now()
        with transaction.atomic():
            Dataset.all_objects.filter(id__in=dataset_ids).update(
                data_catalog=target,
                record_modified=now,
                modified=now,
            )
            if target.id == self.DAAS_CATALOG_ID:
                other_service = DataService.objects.filter(
                    id="other", catalog_id=self.DAAS_CATALOG_ID
                ).first()
                if other_service:
                    RemoteResource.objects.filter(
                        dataset_id__in=dataset_ids, data_service__isnull=True
                    ).update(data_service=other_service)
            for dataset in datasets:
                dataset.signal_update()

        self.stdout.write(f"Moved {len(datasets)} datasets to {target.id}.")
