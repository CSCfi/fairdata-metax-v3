from datetime import timedelta
from typing import Iterable, Optional

from django.db import models
from django.db.models import prefetch_related_objects
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.models.catalog_record.dataset import Dataset


class SyncAction(models.TextChoices):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    FLUSH = "flush"  # Hard delete


class V2SyncStatus(models.Model):
    """Status of latest dataset synchronization to V2."""

    id = models.UUIDField(primary_key=True, editable=False)
    # Disable foreign key constraint for dataset relation
    # so dataset being deleted does not prevent tracking its deletion sync.
    # Accessing missing dataset will raise a DoesNotExist exception.
    dataset = models.OneToOneField(
        "Dataset",
        db_constraint=False,
        on_delete=models.DO_NOTHING,
        related_name="sync_status",
    )
    sync_started = models.DateTimeField(null=True, db_index=True)
    sync_files_started = models.DateTimeField(null=True)
    sync_stopped = models.DateTimeField(null=True)
    action = models.TextField(choices=SyncAction.choices, null=True)
    error = models.TextField(blank=True, null=True)

    @property
    def status(self):
        if self.error:
            return "fail"
        if self.sync_stopped:
            return "success"
        return "incomplete"  # Could be still running or someting aborted the sync

    @property
    def duration(self) -> Optional[timedelta]:
        """Return current elapsed duration or total duration if sync has stopped."""
        if not self.sync_started:
            return None
        end = self.sync_stopped or timezone.now()
        return end - self.sync_started

    def __str__(self):
        action = self.action
        return f"Dataset {self.dataset_id} sync {action=} {self.status}"

    def save(self, *args, **kwargs):
        if self.id != self.dataset_id:
            raise ValueError("V2SyncStatus: Expected object id to match dataset.id.")
        return super().save(*args, **kwargs)

    @classmethod
    def prefetch_datasets(cls, statuses: Iterable):
        """Prefetch related datasets for an iterable of statuses."""
        datasets = []
        for status in statuses:
            try:
                datasets.append(status.dataset)
            except Dataset.DoesNotExist:
                pass
        prefetch_related_objects(datasets, *Dataset.common_prefetch_fields)

    class Meta:
        verbose_name_plural = "V2 sync statuses"
        ordering = ["-sync_started"]


class LastSuccessfulV2Sync(models.Model):
    """Timestamp of last successful dataset synchronization to V2."""

    id = models.UUIDField(primary_key=True, editable=False)  # dataset.id
    record_modified = models.DateTimeField(null=True, blank=True)  # dataset.record_modified

    class Meta:
        ordering = ["-record_modified"]
