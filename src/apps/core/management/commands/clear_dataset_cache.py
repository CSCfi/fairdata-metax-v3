from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        cache = caches["serialized_datasets"]
        if isinstance(cache, DummyCache):
            self.stderr.write("The serialized_datasets cache is not enabled")
            return
        cache.clear()
        self.stdout.write("Cleared serialized_datasets cache")
