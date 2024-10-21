import logging
import uuid
from typing import TYPE_CHECKING

from django.db import models

from apps.common.history import SnapshotHistoricalRecords
from apps.common.models import AbstractBaseModel
from apps.users.models import MetaxUser
from apps.users.sso_client import SSOClient

if TYPE_CHECKING:
    from apps.core.models import Dataset, FileSet

logger = logging.getLogger(__name__)


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

    def _get_csc_project_members(self, csc_project) -> list:
        users = []
        try:
            users = SSOClient().get_csc_project_users(csc_project)
        except Exception as e:
            logger.error(f"Failed to get csc_project members: {e}")
        return users

    @property
    def csc_project_members(self) -> list:
        dataset = self.get_context_dataset()
        file_set: FileSet = getattr(dataset, "file_set", None)
        if file_set and (csc_project := file_set.storage.csc_project):
            return self._get_csc_project_members(csc_project)
        return []
