import logging
import traceback

from cachalot.signals import post_invalidation
from django.conf import settings
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, pre_delete
from django.dispatch import Signal, receiver
from django.utils import timezone

from apps.common.locks import lock_sync_dataset
from apps.common.tasks import run_task
from apps.core.models import Dataset, FileSet
from apps.core.models.contract import Contract
from apps.core.models.sync import SyncAction, V2SyncStatus
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
        run_task(instance.update_published)
    elif action == "pre_clear":
        run_task(instance.update_published, exclude_self=True)
    elif action == "pre_remove":
        run_task(
            instance.update_published,
            queryset=instance.files.filter(id__in=pk_set),
            exclude_self=True,
        )
    elif action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()


@receiver(pre_files_deleted, sender=File)
def handle_files_deleted(sender, queryset, **kwargs):
    fileset_ids = queryset.values_list("file_sets").order_by().distinct()
    for fileset in FileSet.all_objects.filter(id__in=fileset_ids):
        fileset.deprecate_dataset()


def sync_dataset_to_v2(dataset: Dataset, action: SyncAction):
    client = MetaxV2Client()
    with transaction.atomic():
        # Lock syncing dataset to prevent multiple syncs to the same dataset at the same time.
        lock_sync_dataset(id=dataset.id)
        if dataset.draft_of:
            lock_sync_dataset(id=dataset.draft_of_id)

        # Use extra_connection for status so it works independently of request transaction
        status = V2SyncStatus(
            id=dataset.id, dataset=dataset, action=action, sync_started=timezone.now()
        )
        status.save(using="extra_connection")
        try:
            if action == SyncAction.CREATE or action == SyncAction.UPDATE:
                created = action == SyncAction.CREATE
                client.update_dataset(dataset, created=created)
                status.sync_files_started = timezone.now()
                status.save()
                client.update_dataset_files(dataset, created=created)
            elif action == SyncAction.DELETE:
                MetaxV2Client().delete_dataset(dataset, soft=True)
            elif action == SyncAction.FLUSH:
                MetaxV2Client().delete_dataset(dataset, soft=False)
        except Exception as e:
            status.error = ""
            resp = getattr(e, "response", None)
            if resp is not None:
                status.error = f"Response status {resp.status_code}:\n {resp.text}\n\n"

            status.error += "".join(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )
        finally:
            status.sync_stopped = timezone.now()
            status.save()


@receiver(post_delete, sender=Dataset)
def delete_dataset_from_v2(sender, instance: Dataset, soft=False, **kwargs):
    """Sync Metax V2 when deleting dataset from v3"""
    if settings.METAX_V2_INTEGRATION_ENABLED and not getattr(instance, "_deleted_in_v2", False):
        action = SyncAction.DELETE if soft else SyncAction.FLUSH
        run_task(sync_dataset_to_v2, dataset=instance, action=action)


@receiver(dataset_updated)
def handle_dataset_updated(sender, instance: Dataset, **kwargs):
    if settings.METAX_V2_INTEGRATION_ENABLED:
        run_task(sync_dataset_to_v2, dataset=instance, action=SyncAction.UPDATE)


@receiver(dataset_created)
def handle_dataset_created(sender, instance: Dataset, **kwargs):
    if settings.METAX_V2_INTEGRATION_ENABLED:
        run_task(sync_dataset_to_v2, dataset=instance, action=SyncAction.CREATE)


@receiver(pre_delete, sender=Dataset)
def handle_dataset_pre_delete(sender, instance: Dataset, **kwargs):
    if instance.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(instance, "file_set", None)
    ):
        run_task(fileset.update_published, exclude_self=True)


@receiver(sync_contract)
def handle_contract_sync(sender, instance: Contract, **kwargs):
    if settings.METAX_V2_INTEGRATION_ENABLED:
        client = MetaxV2Client()
        client.sync_contracts([instance])


@receiver(post_invalidation)
def check_uncacheable_table_invalidation(sender, **kwargs):
    # Tables that will be modified using the "extra_connection" db should be added
    # to CACHALOT_UNCACHABLE_TABLES to prevent cache inconsistencies.
    # Cachalot performs table invalidation at end of transaction so any changes made
    # using "extra_connection" db might not be visible in "default" db cache until the
    # request transaction is committed.
    if (
        kwargs["db_alias"] == "extra_connection"
        and sender not in settings.CACHALOT_UNCACHABLE_TABLES
    ):
        logger.warning(
            f"Table {sender} was modified using 'extra_connection' but "
            "is not in settings.CACHALOT_UNCACHABLE_TABLES"
        )
