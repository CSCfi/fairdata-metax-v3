import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.management.commands._ldap_idm import LdapIdm
from apps.core.models import Dataset
from apps.core.management.initial_data.admin_org_map import admin_org_map

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        ldap_idm = LdapIdm()

        for dataset in Dataset.all_objects.filter(file_set__storage__storage_service="ida"):
            if dataset.metadata_owner.organization in admin_org_map:
                continue  # Skip if organization is in admin_org_map

            if dataset.metadata_owner.admin_organization:
                continue  # Skip if admin_organization is already set

            if admin_org := ldap_idm.check_admin_org_mismatch(dataset.file_set.csc_project):
                if dataset.metadata_owner.organization != admin_org:
                    logger.info(
                        f"Dataset {dataset.id}: Admin org mismatch."
                        + f" Admin_org: {admin_org}"
                        + f" Home_org: {dataset.metadata_owner.organization}"
                    )
        logger.info("Datasets with admin org mismatch checked")
