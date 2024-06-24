import json
import logging

import requests
from django.conf import settings
from django.db import models
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.common.helpers import is_valid_uuid
from apps.common.models import AbstractBaseModel
from apps.core.models.catalog_record import Dataset

logger = logging.getLogger(__name__)


class DatasetMetrics(AbstractBaseModel):
    """A collection of data available for access or download in one or many representations."""

    dataset = models.OneToOneField(to=Dataset, related_name="metrics", on_delete=models.CASCADE)
    downloads_complete_failed = models.IntegerField(default=0, blank=True)
    downloads_complete_successful = models.IntegerField(default=0, blank=True)
    downloads_file_failed = models.IntegerField(default=0, blank=True)
    downloads_file_successful = models.IntegerField(default=0, blank=True)
    downloads_package_failed = models.IntegerField(default=0, blank=True)
    downloads_package_successful = models.IntegerField(default=0, blank=True)
    downloads_partial_failed = models.IntegerField(default=0, blank=True)
    downloads_partial_successful = models.IntegerField(default=0, blank=True)
    downloads_total_failed = models.IntegerField(default=0, blank=True)
    downloads_total_requests = models.IntegerField(default=0, blank=True)
    downloads_total_successful = models.IntegerField(default=0, blank=True)
    views_data_views = models.IntegerField(default=0, blank=True)
    views_details_views = models.IntegerField(default=0, blank=True)
    views_events_views = models.IntegerField(default=0, blank=True)
    views_maps_views = models.IntegerField(default=0, blank=True)
    views_total_views = models.IntegerField(default=0, blank=True)

    metrics_fields = [
        "downloads_complete_failed",
        "downloads_complete_successful",
        "downloads_file_failed",
        "downloads_file_successful",
        "downloads_package_failed",
        "downloads_package_successful",
        "downloads_partial_failed",
        "downloads_partial_successful",
        "downloads_total_failed",
        "downloads_total_requests",
        "downloads_total_successful",
        "views_data_views",
        "views_details_views",
        "views_events_views",
        "views_maps_views",
        "views_total_views",
    ]

    @classmethod
    def fetch(cls, url) -> int:
        """Fetch updated metrics from the API.

        Returns:
            int: Number of created or updated objects."""
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        # From Metrics data select UUIDs that match a dataset in Metax
        dataset_ids = set(data["views"]) | set(data["downloads"])
        dataset_ids = {id for id in dataset_ids if is_valid_uuid(id)}
        found_dataset_ids = set(
            Dataset.all_objects.filter(id__in=dataset_ids).values_list(
                Cast("id", models.TextField()), flat=True
            )
        )

        # Flatten metrics categories, e.g. views.<id>.total_views -> <id>.views_total_views
        datasets = {id: {} for id in found_dataset_ids}
        for category, category_datasets in data.items():
            for id, dataset in category_datasets.items():
                if id in found_dataset_ids:
                    datasets[id].update(
                        {f"{category}_{field}": value for field, value in dataset.items()}
                    )

        # Get existing DatasetMetrics instances and initialize new instances
        instances = {
            str(instance.dataset_id): instance
            for instance in DatasetMetrics.all_objects.filter(dataset_id__in=found_dataset_ids)
        }
        instances.update(
            {id: DatasetMetrics(dataset_id=id) for id in found_dataset_ids if id not in instances}
        )

        # Check for changed values, update modification date if changed
        now = timezone.now()
        for id, dataset in datasets.items():
            changed = False
            instance = instances[id]
            if instance.removed:
                changed = True
            for field in cls.metrics_fields:
                old_value = getattr(instance, field)
                new_value = dataset.get(field, 0)
                if new_value != old_value:
                    changed = True
                    setattr(instance, field, new_value)
            if changed:
                instance.modified = now
                instance.removed = None
            else:
                instances.pop(id)  # No need to update

        DatasetMetrics.all_objects.bulk_create(
            instances.values(),
            batch_size=1000,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=cls.metrics_fields + ["modified", "removed"],
        )
        return len(instances)
