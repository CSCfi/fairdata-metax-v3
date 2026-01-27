import logging
import json
from django.db import transaction
from django.core.management.base import BaseCommand
from apps.users.models import AdminOrganization


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Load admin organizations from initial_data/admin_organizations.json."""

    def get_manual_rems_approval_organizations(self):
        from apps.core.models import Dataset, REMSApprovalType

        return list(
            Dataset.objects.filter(
                access_rights__rems_approval_type=REMSApprovalType.MANUAL
            ).values_list("metadata_owner__admin_organization", flat=True)
        )

    @transaction.atomic
    def handle(self, *args, **options):
        with open(
            "src/apps/users/management/initial_data/admin_organizations.json",
            "r",
        ) as f:
            admin_organizations = json.load(f)

        manual_rems_approval_organizations = self.get_manual_rems_approval_organizations()

        for admin_organization in admin_organizations:  # pragma: no cover
            allow_manual_rems = admin_organization.get("allow_manual_rems_approval", False)
            if (
                admin_organization["id"] in manual_rems_approval_organizations
                and not allow_manual_rems
            ):
                logger.info(
                    f"Organization {admin_organization["id"]} has manual REMS approval datasets, "
                    "forcing allow_manual_rems_approval=True"
                )
                allow_manual_rems = True

            admin_org, created = AdminOrganization.objects.get_or_create(
                id=admin_organization["id"],
                defaults={
                    "allow_manual_rems_approval": allow_manual_rems,
                    "pref_label": admin_organization["pref_label"],
                },
            )
            if created:
                logger.info(f"Created admin organization: {admin_org}")
            else:
                admin_org.pref_label = admin_organization["pref_label"]
                admin_org.allow_manual_rems_approval = allow_manual_rems
                admin_org.save()
                logger.info(f"Updated admin organization: {admin_org}")

        admin_org_count = AdminOrganization.objects.count()

        self.stdout.write("admin organizations created and updated successfully")
        self.stdout.write(f"Total admin organizations: {admin_org_count}")
