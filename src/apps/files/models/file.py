# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import SoftDeletableModel

from apps.common.models import SystemCreatorBaseModel
from apps.common.serializers.fields import ChecksumField

from .file_storage import FileStorage


class File(SystemCreatorBaseModel, SoftDeletableModel):
    """A file stored in external data storage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # timestamp fields prefixed with record_ to avoid confusion with values from storage service
    record_created = AutoCreatedField(_("created"))
    record_modified = AutoLastModifiedField(_("modified"))

    storage_identifier = models.CharField(
        max_length=200, null=True, help_text=_("Identifier of file in external storage service")
    )
    filename = models.TextField()
    directory_path = models.TextField(db_index=True)  # not directly exposed in the API
    size = models.BigIntegerField(default=0, help_text=_("File size in bytes."))

    checksum = models.TextField(
        help_text=_(
            "Checksum as a lowercase string in format 'algorithm:value'. Allowed algorithms: {}"
        ).format(ChecksumField.allowed_algorithms)
    )

    frozen = models.DateTimeField(null=True, blank=True, db_index=True)
    modified = models.DateTimeField()
    removed = models.DateTimeField(null=True, blank=True)

    # TODO: characteristics = JSONField(blank=True, null=True)
    # TODO?: characteristics_extension = JSONField(blank=True, null=True)

    storage = models.ForeignKey(FileStorage, related_name="files", on_delete=models.CASCADE)
    is_pas_compatible = models.BooleanField(default=None, null=True)

    user = models.CharField(max_length=200, null=True, blank=True)

    @property
    def pathname(self) -> str:
        return f"{self.directory_path}{self.filename}"

    @pathname.setter
    def pathname(self, value: str):
        path, name = value.rsplit("/", 1)
        self.filename = name
        self.directory_path = f"{path}/"

    @property
    def csc_project(self) -> str:
        if self.storage:
            return self.storage.csc_project

    @property
    def storage_service(self) -> str:
        if self.storage.storage_service:
            return self.storage.storage_service

    class Meta:
        index_together = [
            ("directory_path", "storage"),
            ("directory_path", "filename"),
        ]
        ordering = ["directory_path", "filename"]

        constraints = [
            models.CheckConstraint(
                check=~models.Q(filename=""),
                name="%(app_label)s_%(class)s_require_filename",
            ),
            models.CheckConstraint(
                check=models.Q(directory_path__startswith="/")
                & models.Q(directory_path__endswith="/"),
                name="%(app_label)s_%(class)s_require_dir_slash",
            ),
            # pathname should be unique for storage
            models.UniqueConstraint(
                fields=["filename", "directory_path", "storage"],
                condition=models.Q(is_removed=False),
                name=",%(app_label)s_%(class)s_unique_file_path",
            ),
            # identifier should be unique for storage
            models.UniqueConstraint(
                fields=["storage_identifier", "storage"],
                condition=models.Q(is_removed=False) & models.Q(storage_identifier__isnull=False),
                name="%(app_label)s_%(class)s_unique_identifier",
            ),
        ]

    def delete(self, using=None, soft=True, *args, **kwargs):
        """Override delete method to add record_removed"""
        self.removed = timezone.now()
        return super().delete(using=using, soft=soft, *args, **kwargs)
