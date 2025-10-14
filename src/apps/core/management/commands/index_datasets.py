from argparse import ArgumentParser
from typing import List

from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.core.management.base import BaseCommand
from django.db.models import Value, prefetch_related_objects
from django.db import transaction
from rest_framework.serializers import ListSerializer

from apps.common.helpers import batched
from apps.core.cache import DatasetSerializerCache
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.catalog_record.dataset_index import DatasetIndexEntry
from apps.core.serializers.dataset_serializer import DatasetSerializer


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
