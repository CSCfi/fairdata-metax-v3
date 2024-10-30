import logging

from django.conf import settings
from django.db.models.signals import m2m_changed, post_delete, pre_delete
from django.dispatch import Signal, receiver

from apps.core.models import Dataset, FileSet
from apps.core.models.contract import Contract
from apps.core.services import MetaxV2Client
from apps.files.models import File
from apps.files.signals import pre_files_deleted

logger = logging.getLogger(__name__)

dataset_updated = Signal()
dataset_created = Signal()
sync_contract = Signal()  # Called when contract is updated


@receiver(m2m_changed, sender=FileSet.files.through)
def handle_fileset_files_changed(sender, instance: FileSet, action, pk_set, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return
    if action == "post_add":
        instance.update_published()
    elif action == "pre_clear":
        instance.update_published(exclude_self=True)
    elif action == "pre_remove":
        instance.update_published(queryset=instance.files.filter(id__in=pk_set), exclude_self=True)
    elif action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()


@receiver(pre_files_deleted, sender=File)
def handle_files_deleted(sender, queryset, **kwargs):
    fileset_ids = queryset.values_list("file_sets").order_by().distinct()
    for fileset in FileSet.all_objects.filter(id__in=fileset_ids):
        fileset.deprecate_dataset()


@receiver(post_delete, sender=Dataset)
def delete_dataset_from_v2(sender, instance: Dataset, soft=False, **kwargs):
    """Sync Metax V2 when deleting dataset from v3"""
    if settings.METAX_V2_INTEGRATION_ENABLED:
        MetaxV2Client().delete_dataset(instance, soft=soft)


@receiver(dataset_updated)
def handle_dataset_updated(sender, instance: Dataset, **kwargs):
    if instance.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(instance, "file_set", None)
    ):
        fileset.update_published()

    if settings.METAX_V2_INTEGRATION_ENABLED:
        client = MetaxV2Client()
        client.update_dataset(instance)
        client.update_dataset_files(instance)


@receiver(dataset_created)
def handle_dataset_created(sender, instance: Dataset, **kwargs):
    if instance.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(instance, "file_set", None)
    ):
        fileset.update_published()

    if settings.METAX_V2_INTEGRATION_ENABLED:
        client = MetaxV2Client()
        client.update_dataset(instance, created=True)
        client.update_dataset_files(instance, created=True)


@receiver(pre_delete, sender=Dataset)
def handle_dataset_pre_delete(sender, instance: Dataset, **kwargs):
    if instance.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(instance, "file_set", None)
    ):
        fileset.update_published(exclude_self=True)


@receiver(sync_contract)
def handle_contract_sync(sender, instance: Contract, **kwargs):
    if settings.METAX_V2_INTEGRATION_ENABLED:
        client = MetaxV2Client()
        client.sync_contracts([instance])
