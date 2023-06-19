# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import uuid
from typing import Dict

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import AbstractBaseModel

from .file_storage import FileStorage

checksum_algorithm_choices = (
    ("SHA-256", "SHA-256"),
    ("MD5", "MD5"),
    ("SHA-512", "SHA-512"),
)


class File(AbstractBaseModel):
    """A file stored in external data storage."""

    # File id is provided by external service
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    file_storage_identifier = models.CharField(
        max_length=200, null=True, help_text=_("Identifier of file in external service")
    )
    file_storage_pathname = models.CharField(
        max_length=4096, null=True, help_text=_("Path of file in external service")
    )
    file_name = models.TextField()
    directory_path = models.TextField(db_index=True)
    byte_size = models.BigIntegerField(default=0)

    checksum_algorithm = models.CharField(choices=checksum_algorithm_choices, max_length=200)
    checksum_checked = models.DateTimeField()
    checksum_value = models.TextField()

    date_frozen = models.DateTimeField(null=True, blank=True)
    date_deleted = models.DateTimeField(null=True)
    date_uploaded = models.DateTimeField()
    file_modified = models.DateTimeField()

    # TODO(?): open_access (boolean, IDA always sets this to True)
    # TODO: file_characteristics = JSONField(blank=True, null=True)
    # TODO: file_characteristics_extension = JSONField(blank=True, null=True)

    file_storage = models.ForeignKey(FileStorage, related_name="files", on_delete=models.CASCADE)
    is_pas_compatible = models.BooleanField(default=None, null=True)

    @property
    def file_path(self) -> str:
        return f"{self.directory_path}{self.file_name}"

    @file_path.setter
    def file_path(self, value: str):
        path, name = value.rsplit("/", 1)
        self.file_name = name
        self.directory_path = f"{path}/"

    @property
    def project_identifier(self) -> str:
        if self.file_storage:
            return self.file_storage.project_identifier

    @property
    def storage_service(self) -> str:
        if self.file_storage.storage_service:
            return self.file_storage.storage_service

    @property
    def checksum(self) -> Dict:
        return {
            "algorithm": self.checksum_algorithm,
            "checked": self.checksum_checked,
            "value": self.checksum_value,
        }

    @checksum.setter
    def checksum(self, checksum: Dict):
        self.checksum_algorithm = checksum.get("algorithm")
        self.checksum_checked = checksum.get("checked")
        self.checksum_value = checksum.get("value")

    class Meta:
        index_together = [
            ("directory_path", "file_storage"),
            ("directory_path", "file_name"),
        ]
        ordering = ["directory_path", "file_name"]

        constraints = [
            models.CheckConstraint(
                check=~models.Q(file_name=""),
                name="%(app_label)s_%(class)s_require_file_name",
            ),
            models.CheckConstraint(
                check=models.Q(directory_path__startswith="/")
                & models.Q(directory_path__endswith="/"),
                name="%(app_label)s_%(class)s_require_dir_slash",
            ),
            # file_path should be unique for file_storage
            models.UniqueConstraint(
                fields=["file_name", "directory_path", "file_storage"],
                condition=models.Q(is_removed=False),
                name="%(app_label)s_%(class)s_unique_file_path",
            ),
            # file_storage_identifier should be unique for file_storage
            models.UniqueConstraint(
                fields=["file_storage_identifier", "file_storage"],
                condition=models.Q(is_removed=False)
                & models.Q(file_storage_identifier__isnull=False),
                name="%(app_label)s_%(class)s_unique_file_storage_identifier",
            ),
            # file_storage_pathname should be unique for file_storage
            models.UniqueConstraint(
                fields=["file_storage_pathname", "file_storage"],
                condition=models.Q(is_removed=False)
                & models.Q(file_storage_pathname__isnull=False),
                name="%(app_label)s_%(class)s_unique_file_storage_pathname",
            ),
        ]
