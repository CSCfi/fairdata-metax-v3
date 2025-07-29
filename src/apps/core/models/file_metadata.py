import logging
import uuid
from typing import Optional

from django.db import models

from apps.common.copier import ModelCopier
from apps.common.helpers import omit_empty
from apps.files.models import File, FileStorage
from apps.refdata.models import AbstractConcept

from .concepts import FileType, UseCategory

logger = logging.getLogger(__name__)


def refdata_to_legacy(concept: Optional[AbstractConcept]):
    if not concept:
        return None
    return {"identifier": concept.url}


class FileSetFileMetadata(models.Model):
    """Model for additional metadata for dataset-file relation."""

    copier = ModelCopier(copied_relations=[], parent_relations=["file_set"])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_set = models.ForeignKey(
        "core.FileSet", related_name="file_metadata", editable=False, on_delete=models.CASCADE
    )
    file = models.ForeignKey(File, related_name="dataset_metadata", on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    file_type = models.ForeignKey(FileType, null=True, on_delete=models.SET_NULL)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)

    def to_legacy(self):
        return omit_empty(
            {
                "identifier": str(self.file.storage_identifier),
                "title": self.title,
                "description": self.description,
                "file_type": refdata_to_legacy(self.file_type),
                "use_category": refdata_to_legacy(self.use_category),
            }
        )

    class Meta:
        ordering = ["id"]
        unique_together = [("file_set", "file")]


class FileSetDirectoryMetadata(models.Model):
    """Model for additional metadata for dataset-directory relation."""

    copier = ModelCopier(copied_relations=[], parent_relations=["file_set"])

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_set = models.ForeignKey(
        "core.FileSet", related_name="directory_metadata", editable=False, on_delete=models.CASCADE
    )
    pathname = models.TextField(db_index=True)
    storage = models.ForeignKey(FileStorage, on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    use_category = models.ForeignKey(UseCategory, null=True, on_delete=models.SET_NULL)

    def to_legacy(self):
        path = self.pathname
        if path != "/" and path.endswith("/"):
            path = path[:-1]  # Remove trailing slash for V2
        return omit_empty(
            {
                "directory_path": path,
                "title": self.title,
                "description": self.description,
                "use_category": refdata_to_legacy(self.use_category),
            }
        )

    class Meta:
        ordering = ["id"]
        unique_together = [("file_set", "pathname")]
