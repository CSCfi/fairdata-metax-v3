import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.db.models.expressions import Case, When, Value

from apps.core.models import Dataset, MetadataProvider
from apps.core.management.commands._ldap_idm import LdapIdm
from apps.core.management.initial_data.admin_org_map import admin_org_map
from apps.users.models import AdminOrganization

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        # Update admin_organization for each MetadataProvider
        # - When admin_organization is not None, keep current value
        # - When organization is in admin_org_map, use the mapped value as admin_organization
        # - When organization matches an AdminOrganization, use it as admin_organization
        # - When organization is not in admin_org_map or AdminOrganization list, set admin_organization=None
        ldap_idm = LdapIdm()
        cases = []
        for org, admin_org in admin_org_map.items():
            cases.append(When(organization=org, then=Value(admin_org))),
        for _id in AdminOrganization.objects.values_list("id", flat=True):
            cases.append(When(organization=_id, then=Value(_id))),
        logger.info("Updating MetadataProvider admin_organization values")
        MetadataProvider.all_objects.filter(admin_organization__isnull=True).update(
            admin_organization=Case(*cases, default=Value(None))
        )

        # Use quota granter as admin_organization for IDA datasets
        logger.info("Updating admin_organizations from quota granter org")
        num_datasets = 0
        for dataset in Dataset.all_objects.filter(
            file_set__storage__storage_service="ida"
        ).prefetch_related("metadata_owner", "metadata_owner__user"):
            if dataset.metadata_owner.organization in admin_org_map:
                continue  # Skip checking for quota granter for admin_org_map

            if admin_org := ldap_idm.check_admin_org_mismatch(dataset.file_set.csc_project):
                if (
                    admin_org == dataset.metadata_owner.admin_organization
                    or not AdminOrganization.objects.filter(id=admin_org).exists()
                ):
                    continue  # No need to change admin_organization

                metadata_provider, _ = MetadataProvider.objects.get_or_create(
                    user=dataset.metadata_owner.user,
                    organization=dataset.metadata_owner.organization,
                    admin_organization=admin_org,
                )

                if dataset.metadata_owner == metadata_provider:
                    continue

                dataset.metadata_owner = metadata_provider
                dataset.save()
                logger.info(
                    f"Added metadata provider {metadata_provider.id} to dataset {dataset.id}"
                )
                num_datasets += 1

        for metadata_provider in MetadataProvider.objects.filter(datasets__isnull=True):
            metadata_provider.delete()
            logger.info(f"Deleted orphaned metadata provider {metadata_provider.id}")

        logger.info(f"Populated {num_datasets} datasets with quota granter org")
