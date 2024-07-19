import uuid
from typing import TYPE_CHECKING

from django.db import models

from apps.common.history import SnapshotHistoricalRecords
from apps.common.models import AbstractBaseModel
from apps.users.models import MetaxUser

if TYPE_CHECKING:
    from apps.core.models import Dataset


class PermissionRole(models.TextChoices):
    """Permission role for EditorPermission."""

    CREATOR = "creator"
    EDITOR = "editor"


class DatasetPermissions(AbstractBaseModel):
    """Shared permissions between linked copies of same dataset."""

    editors = models.ManyToManyField(MetaxUser, related_name="dataset_edit_permissions")

    # When importing a legacy dataset, Editor additions/removals older than the
    # legacy_modified timestamp are ignored and assumed to have already been handled.
    legacy_modified = models.DateTimeField(
        null=True, blank=True, help_text="Latest modification from legacy Metax."
    )

    history = SnapshotHistoricalRecords(m2m_fields=[editors])

    def set_context_dataset(self, dataset):
        self.context_dataset = dataset

    def get_context_dataset(self):
        if dataset := getattr(self, "context_dataset", None):
            return dataset
        raise ValueError("Dataset-specific properties need context_dataset to be set")

    @property
    def creators(self) -> list:
        return [self.get_context_dataset().metadata_owner.user]
