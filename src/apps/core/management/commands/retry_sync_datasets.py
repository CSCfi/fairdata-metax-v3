from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from apps.common.locks import lock_sync_dataset
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.sync import SyncAction, V2SyncStatus
from apps.core.signals import sync_dataset_to_v2


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing = []

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--identifiers",
            "-ids",
            nargs="+",
            type=str,
            help="List of Metax V3 identifiers to sync to V2",
        )

        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            default=False,
            help="Force sync of listed datasets. Otherwise only failed syncs are retried.",
        )

        parser.add_argument(
            "--clean-missing",
            "-c",
            action="store_true",
            default=False,
            help="Remove SyncStatus entries where V3 dataset is not found.",
        )

    def do_sync(self, statuses):
        V2SyncStatus.prefetch_datasets(statuses)

        # Sync dataset for each sync status object
        for status in statuses:
            with transaction.atomic():
                self.stdout.write(f"Syncing {status.dataset_id} {status.action}")
                dataset: Dataset
                try:
                    dataset = status.dataset
                except Dataset.DoesNotExist:
                    if status.action == SyncAction.DELETE or status.action == SyncAction.FLUSH:
                        dataset = Dataset(id=status.dataset_id)
                    else:
                        self.stderr.write(
                            f"- Dataset {status.dataset_id} does not exist in V3, skipping\n"
                        )
                        self.missing.append(status.dataset_id)
                        continue

                if not lock_sync_dataset(dataset.id, block=False):
                    self.stderr.write(
                        f"- Dataset {status.dataset_id} is locked for syncing, skipping\n"
                    )
                    continue

                sync_dataset_to_v2(dataset, status.action, force_update=True)
                status.refresh_from_db()
                if status.error:
                    self.stderr.write(f"- {status.error}\n")
                else:
                    self.stdout.write(f"- Synced in {status.duration.total_seconds()}s")

    def get_failed_syncs(self, queryset):
        q_error = Q(error__isnull=False)
        q_incomplete = Q(sync_stopped__isnull=True)

        queryset = queryset.filter(q_error | q_incomplete).distinct()
        counts = {
            action["action"]: action["count"]
            for action in queryset.values("action").annotate(count=Count("*")).order_by("action")
        }
        if counts:
            self.stdout.write("Failed syncs:")
            for action, count in counts.items():
                self.stdout.write(f"- {action}: {count}")
        else:
            self.stdout.write("No failed syncs found")
        return queryset

    def handle(self, *args, **options):
        clean_missing = options["clean_missing"]
        force = options["force"]
        identifiers = options["identifiers"]

        queryset = V2SyncStatus.objects.prefetch_related("dataset")
        if identifiers:
            queryset = queryset.filter(dataset_id__in=identifiers)

        if force:
            if not identifiers:
                raise ValueError("The --force argument should used with --identifiers.")
            statuses = list(queryset)
            by_id = {str(status.dataset_id): status for status in statuses}
            for id in identifiers:
                if id not in by_id:
                    statuses.append(V2SyncStatus(id=id, dataset_id=id, action=SyncAction.UPDATE))
        else:
            queryset = self.get_failed_syncs(queryset)
            statuses = list(queryset)

        self.do_sync(statuses)
        if clean_missing:
            V2SyncStatus.objects.filter(dataset_id__in=self.missing).delete()
