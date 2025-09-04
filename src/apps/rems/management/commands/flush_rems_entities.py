from django.core.management import BaseCommand
from django.db import transaction

from apps.rems.models import (
    REMSCatalogueItem,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)

models = [
    REMSCatalogueItem,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
]


class Command(BaseCommand):
    help = """Deletes all REMS entities from the Metax database.
    Does not delete anything from REMS."""

    def handle(self, *args, **options):
        self.stdout.write("Flushing all REMS entities")
        with transaction.atomic():
            for model in models:
                count = model.all_objects.count()
                model.all_objects.all().delete()
                self.stdout.write(f"{model.__name__}: Deleted {count} objects.")
