import logging
from typing import List

import factory.random
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.core import factories
from apps.core.models import Dataset, DatasetMetrics

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--fake-datasets",
            nargs="+",
            type=str,
            help="List of dataset identifiers to generate fake metrics for",
        )

    def fake_metrics(self, identifiers: List[str]) -> int:
        """Generate random metrics values for datasets."""
        self.stdout.write("Generating fake metrics")
        factory.random.reseed_random(seed=None)  # determine seed automatically
        existing_datasets = {
            str(d["id"]) for d in Dataset.objects.filter(id__in=identifiers).values("id")
        }
        metrics = []
        for identifier in identifiers:
            if identifier not in existing_datasets:
                self.stderr.write(f"Dataset not found: {identifier}")
                continue
            metrics.append(factories.DatasetMetricsFactory.build(dataset_id=identifier))
        instances = DatasetMetrics.all_objects.bulk_create(
            metrics,
            update_conflicts=True,
            update_fields=DatasetMetrics.metrics_fields,
            unique_fields=["dataset"],
        )
        return len(instances)

    def fetch_metrics(self):
        url = settings.METRICS_REPORT_URL
        if not url:
            self.stderr.write("Missing settings.METRICS_REPORT_URL")
            return
        self.stdout.write(f"Fetching metrics from {url}")
        return DatasetMetrics.fetch(url)

    def handle(self, *args, **options):
        count = 0
        if identifiers := options.get("fake_datasets"):
            count = self.fake_metrics(identifiers)
        else:
            count = self.fetch_metrics()
        self.stdout.write(f"Created or updated metrics for {count} datasets")
