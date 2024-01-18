import logging

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.core.models import FileSet, LegacyDataset

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LegacyDataset)
def post_process_legacy_dataset(sender, instance: LegacyDataset, **kwargs):
    instance.post_process_dataset_for_v3()
    diff = instance.check_compatibility()
    # use update to not invoke another post_save signal
    LegacyDataset.objects.filter(id=instance.id).update(v2_dataset_compatibility_diff=diff)
    instance.dataset.save()


@receiver(m2m_changed, sender=FileSet.files.through)
def handle_files_changed(sender, instance: FileSet, action, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return

    if action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()
