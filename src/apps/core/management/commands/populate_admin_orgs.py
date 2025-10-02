import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from apps.core.models import Dataset, MetadataProvider
from apps.core.management.commands._ldap_idm import LdapIdm

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        ldap_idm = LdapIdm()

        MetadataProvider.objects.update(admin_organization=F("organization"))
        num_datasets = 0
        for dataset in Dataset.all_objects.filter(file_set__storage__storage_service="ida"):
            if admin_org := ldap_idm.check_admin_org_mismatch(dataset.file_set.csc_project):
                metadata_provider, _ = MetadataProvider.objects.get_or_create(
                    user=dataset.metadata_owner.user,
                    organization=dataset.metadata_owner.organization,
                    admin_organization=admin_org,
                )
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
