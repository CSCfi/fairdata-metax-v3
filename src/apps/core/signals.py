import logging

from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from apps.core.models import Dataset, LegacyDataset

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=LegacyDataset)
def adapt_legacy_dataset_to_v3(sender, instance: LegacyDataset, **kwargs):
    attached_instances = instance.prepare_dataset_for_v3()
    logger.info(f"prepared {attached_instances=}")


@receiver(post_save, sender=LegacyDataset)
def post_process_legacy_dataset(sender, instance: LegacyDataset, **kwargs):
    attached_instances = instance.post_process_dataset_for_v3()
    logger.info(f"post processed {attached_instances=}")


@receiver(m2m_changed, sender=Dataset.files.through)
def handle_files_changed(sender, instance: Dataset, action, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return

    if action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()
