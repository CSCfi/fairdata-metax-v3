from django.core.management import BaseCommand
from django.db.models import Q, Exists, OuterRef

from apps.rems.rems_service import REMSService, REMSResource


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.service = REMSService()
        from apps.core import factories
        from apps.core.models import Dataset
        from apps.core.models.access_rights import AccessTypeChoices

        rems_dataset_filter = Q(
            access_rights__access_type__url=AccessTypeChoices.PERMIT,
            access_rights__rems_approval_type__isnull=False,
            data_catalog__rems_enabled=True,
        )

        rems_datasets = (
            Dataset.objects.filter(state="published")
            .filter(rems_dataset_filter)
            .prefetch_related("rems_resources")
        )

        self.stdout.write(f"Syncing {len(rems_datasets)} datasets to REMS")
        for dataset in rems_datasets:
            self.service.publish_dataset(dataset)
            if dataset.rems_publish_error:
                self.stderr.write(dataset.rems_publish_error)

        # Unpublish datasets that should no longer be in REMS but have an active REMSResource
        rems_datasets_to_unpublish = (
            Dataset.objects.filter(state="published")
            .exclude(rems_dataset_filter)
            .filter(Exists(REMSResource.objects.filter(dataset_id=OuterRef("id"))))
            .prefetch_related("rems_resources")
        )
        self.stdout.write(f"Unpublishing {len(rems_datasets_to_unpublish)} datasets in REMS")
        for dataset in rems_datasets_to_unpublish:
            self.service.unpublish_dataset(dataset)
            if dataset.rems_publish_error:
                self.stderr.write(dataset.rems_publish_error)
