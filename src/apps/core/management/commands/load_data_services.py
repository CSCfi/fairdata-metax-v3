import json
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import DataCatalog, DataService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Load data services from initial_data/data_services.json."""

    @transaction.atomic
    def handle(self, *args, **options):
        with open(
            "src/apps/core/management/initial_data/data_services.json",
            "r",
        ) as f:
            data_services = json.load(f)

        json_ids = {data_service["id"] for data_service in data_services}
        DataService.objects.exclude(id__in=json_ids).delete()

        for data_service in data_services:
            catalog_id = data_service["catalog"]
            catalog = DataCatalog.objects.get(id=catalog_id)

            ds, created = DataService.objects.get_or_create(
                id=data_service["id"],
                defaults={
                    "catalog": catalog,
                    "pref_label": data_service["pref_label"],
                },
            )
            if created:
                logger.info("Created data service: %s", ds)
            else:
                updated_fields = []

                if ds.catalog_id != catalog.id:
                    ds.catalog = catalog
                    updated_fields.append("catalog")

                if ds.pref_label != data_service["pref_label"]:
                    ds.pref_label = data_service["pref_label"]
                    updated_fields.append("pref_label")

                if updated_fields:
                    ds.save(update_fields=updated_fields)

        self.stdout.write("data services created and updated successfully")
        self.stdout.write(f"Total data services: {DataService.objects.count()}")

