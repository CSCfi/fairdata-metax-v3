import logging
import json
from django.db import transaction
from django.core.management.base import BaseCommand
from apps.users.models import AdminOrganization


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Load admin organizations from initial_data/admin_organizations.json."""

    @transaction.atomic
    def handle(self, *args, **options):
        with open(
            "src/apps/users/management/initial_data/admin_organizations.json",
            "r",
        ) as f:
            admin_organizations = json.load(f)
        for admin_organization in admin_organizations:  # pragma: no cover
            admin_org, created = AdminOrganization.objects.get_or_create(
                id=admin_organization["id"],
                defaults={
                    "pref_label": admin_organization["pref_label"],
                },
            )
            if created:
                logger.info(f"Created admin organization: {admin_org}")
            else:
                admin_org.pref_label = admin_organization["pref_label"]
                admin_org.save()
                logger.info(f"Updated admin organization: {admin_org}")

        admin_org_count = AdminOrganization.objects.count()

        self.stdout.write("admin organizations created and updated successfully")
        self.stdout.write(f"Total admin organizations: {admin_org_count}")
