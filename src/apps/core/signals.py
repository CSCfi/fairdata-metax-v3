import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.core.models import LegacyDataset

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=LegacyDataset)
def adapt_legacy_dataset_to_v3(sender, instance: LegacyDataset, **kwargs):
    attached_instances = instance.prepare_dataset_for_v3()
    logger.info(f"prepared {attached_instances=}")


@receiver(post_save, sender=LegacyDataset)
def post_process_legacy_dataset(sender, instance: LegacyDataset, **kwargs):
    attached_instances = instance.post_process_dataset_for_v3()
    logger.info(f"post processed {attached_instances=}")
