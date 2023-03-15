import logging

from django.db import models

from apps.files.models import File, StorageProject

from .concepts import FileType, UseCategory

logger = logging.getLogger(__name__)


class DatasetFileMetadata(models.Model):
    """Model for additional metadata for dataset-file relation."""

    dataset = models.ForeignKey(
        "core.Dataset", related_name="file_metadata", on_delete=models.CASCADE
    )
    file = models.ForeignKey(File, related_name="dataset_metadata", on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    file_type = models.ForeignKey(FileType, null=True, on_delete=models.SET_NULL)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("dataset", "file")]


class DatasetDirectoryMetadata(models.Model):
    """Model for additional metadata for dataset-directory relation."""

    dataset = models.ForeignKey(
        "core.Dataset",
        related_name="directory_metadata",
        editable=False,
        on_delete=models.CASCADE,
    )
    directory_path = models.TextField(db_index=True)
    storage_project = models.ForeignKey(StorageProject, on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)
