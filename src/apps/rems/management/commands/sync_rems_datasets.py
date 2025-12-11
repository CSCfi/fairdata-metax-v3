from django.core.management import BaseCommand
from django.db.models import Exists, OuterRef, Q

from apps.core.models import Dataset
from apps.core.models.access_rights import AccessTypeChoices
from apps.rems.rems_service import REMSResource, REMSService


class Command(BaseCommand):
    help = """Updates all REMS-enabled datasets in REMS."""

    def handle(self, *args, **options):
        self.service = REMSService()

        rems_datasets = Dataset.objects.rems_datasets().prefetch_related("rems_resources")

        self.stdout.write(f"Syncing {len(rems_datasets)} datasets to REMS")
        for dataset in rems_datasets:
            self.service.publish_dataset(dataset)
            if dataset.rems_publish_error:
                self.stderr.write(dataset.rems_publish_error)

        # Unpublish datasets that should no longer be in REMS but have an active REMSResource
        rems_datasets_to_unpublish = (
            Dataset.objects.rems_datasets(exclude=True)
            .filter(Exists(REMSResource.objects.filter(dataset_id=OuterRef("id"))))
            .prefetch_related("rems_resources")
        )
        self.stdout.write(f"Unpublishing {len(rems_datasets_to_unpublish)} datasets in REMS")
        for dataset in rems_datasets_to_unpublish:
            self.service.unpublish_dataset(dataset)
            if dataset.rems_publish_error:
                self.stderr.write(dataset.rems_publish_error)
