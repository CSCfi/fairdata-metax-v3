import logging

from django.db import models

from apps.common.copier import ModelCopier
from apps.common.models import AbstractBaseModel
from apps.files.models import File, FileStorage

from .concepts import FileType, UseCategory

logger = logging.getLogger(__name__)


class FileSetFileMetadata(models.Model):
    """Model for additional metadata for dataset-file relation."""

    copier = ModelCopier(copied_relations=[], parent_relations=["file_set"])

    file_set = models.ForeignKey(
        "core.FileSet", related_name="file_metadata", editable=False, on_delete=models.CASCADE
    )
    file = models.ForeignKey(File, related_name="dataset_metadata", on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    file_type = models.ForeignKey(FileType, null=True, on_delete=models.SET_NULL)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["id"]
        unique_together = [("file_set", "file")]


class FileSetDirectoryMetadata(models.Model):
    """Model for additional metadata for dataset-directory relation."""

    copier = ModelCopier(copied_relations=[], parent_relations=["file_set"])

    file_set = models.ForeignKey(
        "core.FileSet", related_name="directory_metadata", editable=False, on_delete=models.CASCADE
    )
    pathname = models.TextField(db_index=True)
    storage = models.ForeignKey(FileStorage, on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["id"]
        unique_together = [("file_set", "pathname")]
