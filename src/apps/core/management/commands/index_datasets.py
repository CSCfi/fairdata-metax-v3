from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.catalog_record.dataset_index import DatasetIndexEntry


class Command(BaseCommand):
    """Update dataset facet index entries."""

    def handle(self, *args, **options):
        all_datasets = Dataset.objects.prefetch_related(
            "access_rights__access_type", "data_catalog"
        )
        count = 0
        total = len(all_datasets)
        self.stdout.write("Updating index entries for all datasets")
        with transaction.atomic():
            for dataset in all_datasets:
                dataset.update_index()
                count += 1
                if count % 100 == 0 or count == total:
                    self.stdout.write(f"{count}/{total} datasets indexed")

            unused_count, _ = DatasetIndexEntry.objects.filter(datasets__isnull=True).delete()
            if unused_count:
                self.stdout.write(f"{unused_count} unused entries deleted")
        self.stdout.write("All dataset index entries updated")
