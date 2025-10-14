# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import uuid
from typing import Dict, Optional

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField

from apps.common.models import CustomSoftDeletableModel, SystemCreatorBaseModel
from apps.common.serializers.fields import ChecksumField
from apps.files.helpers import convert_checksum_v2_to_v3, convert_checksum_v3_to_v2
from apps.files.models.file_characteristics import FileCharacteristics
from apps.users.models import MetaxUser

from .file_storage import FileStorage


class File(SystemCreatorBaseModel, CustomSoftDeletableModel):
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
    published = models.DateTimeField(null=True, blank=True)

    characteristics = models.OneToOneField(
        FileCharacteristics, related_name="file", on_delete=models.SET_NULL, null=True
    )
    characteristics_extension = models.JSONField(blank=True, null=True)

    storage = models.ForeignKey(FileStorage, related_name="files", on_delete=models.CASCADE)
    is_pas_compatible = models.BooleanField(default=None, null=True, blank=True)
    pas_compatible_file = models.OneToOneField(
        "self",
        related_name="non_pas_compatible_file",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    user = models.CharField(max_length=200, null=True, blank=True)
    legacy_id = models.BigIntegerField(unique=True, null=True, blank=True)
    is_legacy_syncable = models.BooleanField(default=True)

    pas_process_running = models.BooleanField(
        default=False,
        help_text=_("Only PAS service is allowed to update files while PAS is processing them."),
    )

    @classmethod
    def values_from_legacy(
        cls,
        legacy_file: dict,
        storage: FileStorage,
        characteristics: Optional[FileCharacteristics],
    ):
        removed = None
        path, filename = legacy_file["file_path"].rsplit("/", 1)
        directory_path = f"{path}/"
        if legacy_file.get("removed"):
            removed = legacy_file.get("file_deleted") or timezone.now().isoformat()
        return dict(
            storage_identifier=legacy_file["identifier"],
            checksum=convert_checksum_v2_to_v3(legacy_file.get("checksum", {})),
            size=legacy_file.get("byte_size"),
            filename=filename,
            directory_path=directory_path,
            frozen=legacy_file.get("file_frozen"),
            modified=legacy_file.get("file_modified"),
            removed=removed,
            user=legacy_file.get("user_created"),
            storage=storage,
            legacy_id=legacy_file.get("id"),
            is_pas_compatible=legacy_file.get("pas_compatible"),
            characteristics=characteristics,
            characteristics_extension=legacy_file.get("file_characteristics_extension"),
        )

    @classmethod
    def create_from_legacy(
        cls,
        legacy_file: dict,
        storage: Optional[FileStorage] = None,
        characteristics: Optional[FileCharacteristics] = None,
    ):
        if not storage:
            storage = FileStorage.get_or_create_from_legacy(legacy_file)
        return File.all_objects.create(
            **cls.values_from_legacy(legacy_file, storage, characteristics)
        )

    def to_legacy_sync(self):
        """Convert file to format compatible with legacy /files/sync_from_v3"""

        v2_checksum = convert_checksum_v3_to_v2(self.checksum)

        val = {
            "id": self.legacy_id,
            "identifier": self.storage_identifier,
            "file_path": self.pathname,
            "file_uploaded": self.modified,
            "file_modified": self.modified,
            "file_frozen": self.frozen or self.modified,
            "byte_size": self.size,
            "file_storage": settings.V3_STORAGE_SERVICE_TO_LEGACY_FILE_STORAGE[
                self.storage_service
            ],
            "project_identifier": self.csc_project,
            "user_modified": self.user,
            "date_created": self.record_created,
            "date_modified": self.record_modified,
            "date_removed": self.removed,
            "file_deleted": self.removed,
            "removed": True if self.removed else False,
            "checksum_checked": self.modified,
            "checksum_algorithm": v2_checksum.get("algorithm"),
            "checksum_value": v2_checksum.get("checksum_value"),
            "file_characteristics_extension": self.characteristics_extension,
            "file_characteristics": None,
        }
        if self.characteristics:
            val["file_characteristics"] = self.characteristics.to_legacy()

        return val

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

    def get_lock_reason(self, user: MetaxUser) -> Optional[str]:
        """Determine if and why user is locked from modifying the file."""
        if user.is_superuser:
            return None
        if self.pas_process_running and not any(
            group.name == "pas" for group in user.groups.all()
        ):
            return "Only PAS service is allowed to modify the file while it is in PAS process."

        return None

    @classmethod
    def get_lock_reasons_for_queryset(
        cls, user: MetaxUser, queryset: models.QuerySet
    ) -> Dict[uuid.UUID, str]:
        """Determine if and why user is locked from modifying the file."""
        if user.is_superuser or any(group.name == "pas" for group in user.groups.all()):
            return {}

        msg = "Only PAS service is allowed to modify the file while it is in PAS process."
        return {
            _id: msg
            for _id, pas_running in queryset.values_list("id", "pas_process_running")
            if pas_running
        }

    def __str__(self):
        return f"File ({self.id}) {self.filename}"

    class Meta:
        indexes = [
            models.Index(
                fields=("storage", "directory_path"),
                condition=models.Q(removed__isnull=True),
                name="%(app_label)s_%(class)s_storage_directory",
            ),
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
                fields=["storage", "directory_path", "filename"],
                condition=models.Q(removed__isnull=True),
                name="%(app_label)s_%(class)s_unique_file_path",
            ),
            # identifier should be unique for storage
            models.UniqueConstraint(
                fields=["storage", "storage_identifier"],
                condition=models.Q(removed__isnull=True)
                & models.Q(storage_identifier__isnull=False),
                name="%(app_label)s_%(class)s_unique_identifier",
            ),
            # pas_compatible_file cannot refer to file itself
            models.CheckConstraint(
                check=~models.Q(pas_compatible_file=models.F("id")),
                name="%(app_label)s_%(class)s_no_self_pas_compatible_relation",
            ),
        ]
