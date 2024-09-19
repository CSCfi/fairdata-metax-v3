from argparse import ArgumentParser
from typing import List

from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.core.management.base import BaseCommand
from django.db.models import Value, prefetch_related_objects
from rest_framework.serializers import ListSerializer

from apps.common.helpers import batched
from apps.core.cache import DatasetSerializerCache
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.serializers.dataset_serializer import DatasetSerializer


class CacheListSerializer(ListSerializer):
    def __init__(self, *args, stdout, **kwargs):
        self.stdout = stdout
        super().__init__(*args, **kwargs)

    def to_representation(self, data):
        cache = self.child.cache
        rep = []
        for batch in batched(data, 1000):
            rep.extend([self.child.to_representation(item) for item in batch])
            cache.commit_changed_to_source()
            self.stdout.write(f"Cached {len(rep)}/{len(data)} datasets")
        return rep


class CachedFieldsOnlyDatasetSerializer(DatasetSerializer):
    def get_fields(self):
        fields = super().get_fields()
        cached_fields = self.cache.cached_fields
        fields = {name: field for name, field in fields.items() if name in cached_fields}
        return fields


class Command(BaseCommand):
    def prefetch_cachable_fields(self, datasets: List[Dataset], serializer: DatasetSerializer):
        cached_fields = set(serializer.get_cached_field_sources())
        cached_prefetch_fields = []
        for prefetch in Dataset.common_prefetch_fields:
            if type(prefetch) is str:
                prefix = prefetch.split("__", 1)[0]
                if prefix not in cached_fields:
                    continue
            cached_prefetch_fields.append(prefetch)

        prefetch_related_objects(datasets, *cached_prefetch_fields)
        self.stdout.write("Prefetch complete")

    def get_serializer_context(self):
        class View:
            query_params = {}

        dummy_view = View()

        class DummyRequest:
            view = dummy_view
            user = AnonymousUser()

        return {
            "request": DummyRequest,
            "view": dummy_view,
        }

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            required=False,
            default=False,
            help="Refresh cache for all datasets.",
        )

    def handle(self, *args, **options):
        datasets_cache = caches["serialized_datasets"]
        if isinstance(datasets_cache, DummyCache):
            self.stderr.write("The serialized_datasets cache is not enabled")
            return
        self.stdout.write(f"Using {datasets_cache.__class__.__name__} cache backend\n")

        # Mark datasets as prefetched to avoid Dataset.ensure_prefetch
        # from triggering unneeded prefetches
        all_datasets = Dataset.objects.annotate(is_prefetched=Value(True))
        datasets_count = len(all_datasets)
        cache = DatasetSerializerCache(all_datasets, autocommit=False)
        datasets = [dataset for dataset in all_datasets if dataset.id not in cache.values]
        self.stdout.write(
            f"Existing cached datasets: {datasets_count-len(datasets)}/{datasets_count}"
        )

        datasets: List[Dataset]
        if options.get("all"):
            self.stdout.write("Caching all datasets")
            datasets = all_datasets
            cache.clear()
        else:
            self.stdout.write(f"Caching {len(datasets)} uncached datasets")

        serializer = CacheListSerializer(
            datasets,
            child=CachedFieldsOnlyDatasetSerializer(cache=cache),
            context=self.get_serializer_context(),
            stdout=self.stdout,
        )
        self.prefetch_cachable_fields(datasets, serializer.child)
        serializer.data  # Run serialization

        # Check if all datasets are now in cache
        cache.clear()
        cache.fetch_from_source(all_datasets, include_newer=True)
        cached_datasets_count = len(cache.values)
        if datasets_count == cached_datasets_count:
            self.stdout.write("Cache ok")
        else:
            self.stderr.write("Not all datasets are in cache, check your cache limits")
            self.stderr.write(f"Cached datasets: {cached_datasets_count}/{datasets_count}")
