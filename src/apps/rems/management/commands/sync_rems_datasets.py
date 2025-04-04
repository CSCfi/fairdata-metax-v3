from django.core.management import BaseCommand

from apps.rems.rems_service import REMSService


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.service = REMSService()
        from apps.core.models import Dataset
        from apps.core.models.access_rights import AccessTypeChoices

        rems_datasets = Dataset.objects.filter(
            state="published",
            access_rights__access_type__url__in=[
                AccessTypeChoices.PERMIT,
                AccessTypeChoices.RESTRICTED,
            ],
            access_rights__rems_approval_type__isnull=False,
        )

        self.stdout.write(f"Syncing {len(rems_datasets)} datasets to REMS")
        for dataset in rems_datasets:
            self.service.publish_dataset(dataset)
            if dataset.rems_publish_error:
                self.stderr.write(dataset.rems_publish_error)

        # TODO: Remove datasets that should no longer be in REMS
