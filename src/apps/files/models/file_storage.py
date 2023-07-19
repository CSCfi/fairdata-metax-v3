# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


import functools
import operator
import re
import uuid
from collections import namedtuple
from typing import Dict, List, Set, Tuple

from django.conf import settings
from django.db import models
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from model_utils.managers import SoftDeletableManager
from rest_framework import exceptions
from rest_framework.serializers import ValidationError

from apps.common.helpers import get_attr_or_item
from apps.common.managers import ProxyBasePolymorphicManager
from apps.common.models import AbstractBaseModel, ProxyBasePolymorphicModel


class FileStorageManagerMixin(ProxyBasePolymorphicManager):
    """Mixin for managers for FileStorage and its proxy models."""

    def get_for_object(self, object: dict) -> models.Model:
        """Get FileStorage for a dict object.

        Validates input object and returns single FileStorage instance
        based on its storage_service value and FileStorage-specific extra values.
        """
        self.model.validate_object(object)
        try:
            return self.get(
                project_identifier=object["project_identifier"],
                storage_service=object["storage_service"],
            )
        except self.model.DoesNotExist:
            raise exceptions.NotFound()

    def _group_files_by_key(
        self, files: List[dict], raise_exception: bool
    ) -> Dict[tuple, List[dict]]:
        """Group Files by their FileStorage key."""
        files_by_key: Dict[self.model.key_type, List[dict]] = {}
        for f in files:
            try:
                self.model.validate_object(f)
                files_by_key.setdefault(self.model.get_key(f), []).append(f)
            except ValidationError as e:
                if raise_exception:
                    raise e
                f.setdefault("errors", {}).update(e.detail)
                f["file_storage"] = None
        return files_by_key

    def _get_existing_filestorages_by_key(
        self, files_by_key: Dict[tuple, List[dict]]
    ) -> Dict[tuple, List[dict]]:
        """Get FileStorage instances that exist for files by FileStorage key."""
        file_storages_by_key: Dict[self.model.key_type, self.model] = {}
        filters = [models.Q(**key._asdict()) for key in files_by_key]
        if filters:
            combined_filters = functools.reduce(operator.or_, filters)
            queryset = self.filter(combined_filters)
            file_storages_by_key = {self.model.get_key(fs): fs for fs in queryset}
        return file_storages_by_key

    def _create_missing_filestorages(
        self,
        files_by_key: Dict[tuple, List[dict]],
        file_storages_by_key: Dict[tuple, List[dict]],
        allow_create,
        raise_exception,
    ) -> Tuple[Dict[tuple, List[dict]], Dict[str, dict]]:
        """Create missing FileStorage instances.

        If files_by_key contains FileStorage keys that don't exist in
        file_storages_by_key, create them. If creation is not allowed,
        raise exception or return error.

        Returns tuple (modified file_storages_by_key, errors_by_key)."""
        errors_by_key = {}
        missing_storages = [key for key in files_by_key if key not in file_storages_by_key]
        for key in missing_storages:
            try:
                if not allow_create:
                    raise ValidationError({"storage_service": "No matching file storage found."})
                key_dict = key._asdict()
                new_storage = self.model.get_proxy_instance(**key_dict)
                new_storage.save()
                file_storages_by_key[key] = new_storage
            except ValidationError as e:
                if raise_exception:
                    raise e
                errors_by_key[key] = e.detail
        return file_storages_by_key, errors_by_key

    def assign_to_file_data(
        self,
        files: List[dict],
        allow_create=False,
        raise_exception=True,
        remove_filestorage_fields=False,
    ) -> List[dict]:
        """
        Retrieve FileStorage instances and assign to file data.

        Retrieves (or optionally creates) a FileStorage instance for
        each file in files list. The instance is assigned to
        file['file_storage'].

        Files are validated for required FileStorage fields based on
        file['storage_service']. When raise_exception is False and
        an error occurs, the error will be added to file['errors'] dict
        and file['file_storage'] will be set to None.

        Args:
            files: List of dicts containing file data
            allow_create: Create FileStorages that don't exist.
            raise_exception: Raise exception on error. Otherwise add errors to dict.
            remove_filestorage_fields: When enabled, remove storage_location and
                other FileStorage fields from the files.

        Returns:
            files: Modified file data.
        """

        files_by_key = self._group_files_by_key(files, raise_exception=raise_exception)
        file_storages_by_key = self._get_existing_filestorages_by_key(files_by_key)
        file_storages_by_key, errors_by_key = self._create_missing_filestorages(
            files_by_key,
            file_storages_by_key,
            allow_create=allow_create,
            raise_exception=raise_exception,
        )

        # Assign FileStorage instances to data
        for key, key_files in files_by_key.items():
            for f in key_files:
                if f.get("errors"):
                    f["file_storage"] = None
                    continue
                if remove_filestorage_fields:
                    f.pop("storage_service", None)
                    for field in self.model.all_extra_fields:
                        f.pop(field, None)
                f["file_storage"] = file_storages_by_key.get(key)
                if errors := errors_by_key.get(key):
                    f.setdefault("errors", {}).update(errors)
        return files


class SoftDeletableFileStorageManager(FileStorageManagerMixin, SoftDeletableManager):
    pass


class FileStorageManager(FileStorageManagerMixin, models.Manager):
    pass


STORAGE_SERVICE_CHOICES = [(s, s) for s in settings.STORAGE_SERVICE_FILE_STORAGES]


class FileStorage(ProxyBasePolymorphicModel, AbstractBaseModel):
    """FileStorage respresents a collection of files in a storage service."""

    proxy_lookup_field = "storage_service"

    proxy_mapping = settings.STORAGE_SERVICE_FILE_STORAGES

    # Extended SoftDeletableModel managers
    objects = SoftDeletableFileStorageManager(_emit_deprecation_warnings=True)
    available_objects = SoftDeletableFileStorageManager()
    all_objects = FileStorageManager()

    # Fields common for all FileStorage types
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_service = models.CharField(max_length=64, choices=STORAGE_SERVICE_CHOICES)

    # Extra identification fields used only by specific FileStorage types
    project_identifier = models.CharField(max_length=200, null=True, blank=True)
    all_extra_fields = ["project_identifier"]

    # A key should uniquely identify a FileStorage instance
    key_type = namedtuple("FileStorageKey", ["storage_service", *all_extra_fields])

    # Set supported extra fields for model. Extra fields not listed here should be null.
    optional_extra_fields = set()
    required_extra_fields = set()

    # File fields that are unique by FileStorage or file service, validation in Python.
    # Any null values are exempt from the uniqueness check. File path has its own validation
    # and is not listed here.
    unique_file_fields_per_file_storage = ["file_storage_pathname"]
    unique_file_fields_per_storage_service = ["file_storage_identifier"]

    # File fields required by FileStorage that are normally optional, e.g. file_storage_identifier
    required_file_fields = set()

    class Meta:
        unique_together = [("project_identifier", "storage_service")]

    @classmethod
    @functools.lru_cache
    def get_allowed_extra_fields(cls):
        return {*cls.optional_extra_fields, *cls.required_extra_fields}

    @classmethod
    def get_key(cls, object) -> tuple:
        """Uniquely identify a FileStorage instance based on its field values."""
        return cls.key_type(*(get_attr_or_item(object, field) for field in cls.key_type._fields))

    @classmethod
    def remove_unsupported_extra_fields(cls, data: dict) -> dict:
        """Remove disallowed FileService fields from data.

        E.g. remove project_identifier from dict if the current
        FileStorage does not support the project_identifier field."""
        allowed_extra_fields = cls.get_allowed_extra_fields()
        for field in cls.all_extra_fields:
            if field not in allowed_extra_fields:
                data.pop(field, None)
        return data

    @classmethod
    def validate_object(cls, object):
        """Make sure object has required file storage fields as attributes or items.

        Useful for:
        * Checking a FileStorage object is valid and can be saved.
        * Checking that file dict values correspond to a valid FileStorage.
        """
        storage_service = get_attr_or_item(object, "storage_service")
        if not storage_service:
            raise ValidationError({"storage_service": _("Value is required.")})
        if storage_service not in settings.STORAGE_SERVICE_FILE_STORAGES:
            raise ValidationError({"storage_service": _("Invalid storage_service value.")})

        proxy_cls = cls.get_proxy_model(storage_service)
        for field in cls.all_extra_fields:
            required = field in proxy_cls.required_extra_fields
            forbidden = field not in proxy_cls.get_allowed_extra_fields()
            value = get_attr_or_item(object, field)
            error_msg = None
            if required and value is None:
                error_msg = _("Field is required for storage_service='{location}'.")
            elif forbidden and value is not None:
                error_msg = _("Field is not allowed for storage_service='{location}'.")
            if error_msg:
                raise ValidationError({field: error_msg.format(location=storage_service)})

    def __repr__(self):
        relevant_fields = {
            "storage_service",
            *self.required_extra_fields,
            *self.optional_extra_fields,
        }
        values = ", ".join(
            [f"{k}={v}" for k, v in self.key._asdict().items() if k in relevant_fields]
        )
        return f"<{self.__class__.__name__}: {values}>"

    def get_directory_paths(self, file_set=None) -> Set[str]:
        """Get directory paths used in the storage as a set.

        If dataset is supplied, return only directories belonging to dataset.
        Otherwise all directories are returned."""
        qs = self.files
        if file_set:
            qs = qs.filter(file_sets=file_set)
        file_directory_paths = (
            qs.values_list("directory_path", flat=True)
            .order_by("directory_path")
            .distinct("directory_path")
        )
        all_paths = set(file_directory_paths)

        # Add intermediate directories that don't have files directly but in subdirs.
        last_part = re.compile("/[^/]+/$")  # matches e.g. `/subdir/` for `/dir/subdir/`
        for path in file_directory_paths:
            # Remove last path part and add to set until encountering path already in set.
            path = last_part.sub("/", path, count=1)
            while path not in all_paths:
                all_paths.add(path)
                path = last_part.sub("/", path, count=1)
        return all_paths

    def save(self, *args, **kwargs):
        try:
            self.validate_object(self)
        except ValidationError as e:
            raise ValueError(e.detail)
        return super().save(*args, **kwargs)

    @property
    def key(self) -> tuple:
        return self.get_key(self)

    @property
    def params_dict(self):
        return self.remove_unsupported_extra_fields(self.key._asdict())

    # Validation for file data conflics

    @classmethod
    def _group_file_data_by_file_storage(cls, files: List[dict]) -> Dict["FileStorage", dict]:
        files_by_storage = {}
        for f in files:
            if f["file_storage"] is not None:
                files_by_storage.setdefault(f["file_storage"], []).append(f)
        return files_by_storage

    @classmethod
    def _group_file_data_by_storage_service(cls, files: List[dict]) -> Dict[str, dict]:
        files_by_service = {}
        for f in files:
            if f["file_storage"] is not None:
                files_by_service.setdefault(f["file_storage"].storage_service, []).append(f)
        return files_by_service

    @classmethod
    def _check_conflicts_within_new(
        cls, files: List[dict], field, raise_exception=True
    ) -> List[dict]:
        """Check new file data for duplicate values."""
        new_values = set()
        for f in files:
            value = f.get(field)
            if value is not None:
                if value in new_values:
                    errors = {field: _("Duplicate value in request.")}
                    if raise_exception:
                        raise ValidationError(errors)
                    else:
                        f.setdefault("errors", {}).update(errors)
                else:
                    new_values.add(value)
        return files

    @classmethod
    def _check_conflicts_with_existing(
        cls, files: List[dict], queryset, field, raise_exception=True
    ) -> List[dict]:
        """Check file data for conflicts with existing data."""
        new_values = [f[field] for f in files if f.get(field) is not None]
        conflicts = queryset.filter(**{f"{field}__in": new_values}).values(field, "id")
        if conflicts:
            conflicting_id_by_value = {c[field]: c["id"] for c in conflicts}
            for f in files:
                errors = None
                if f.get(field) in conflicting_id_by_value:
                    errors = {
                        field: _("A file with the same value already exists, id='{fid}'.").format(
                            fid=conflicting_id_by_value[f[field]]
                        )
                    }
                if errors:
                    if raise_exception:
                        raise ValidationError(errors)
                    else:
                        f.setdefault("errors", {}).update(errors)
        return files

    @classmethod
    def _check_conflicts(cls, files: List[dict], queryset, field, raise_exception):
        """Check conflicts in file data."""
        files = cls._check_conflicts_within_new(files, field, raise_exception)
        files = cls._check_conflicts_with_existing(files, queryset, field, raise_exception)

    @classmethod
    def _check_file_path_conflicts(cls, files: List[dict], raise_exception):
        """Check file_path conflicts."""
        new_files = [f for f in files if ("id" not in f)]
        new_files_by_storage = cls._group_file_data_by_file_storage(new_files)
        for file_storage, new_storage_files in new_files_by_storage.items():
            new_values = [f["file_path"] for f in files if f.get("file_path")]
            queryset = file_storage.files.filter(
                # prefilter results before doing a more expensive exact match with Concat
                directory_path__in=set(p.rsplit("/", 1)[0] + "/" for p in new_values),
                file_name__in=set(p.rsplit("/", 1)[1] for p in new_values),
            ).annotate(file_path=Concat("directory_path", "file_name"))
            cls._check_conflicts(
                new_storage_files,
                queryset=queryset,
                field="file_path",
                raise_exception=raise_exception,
            )
        return files

    @classmethod
    def _check_file_storage_value_conflicts(cls, files: List[dict], raise_exception):
        """Check conflicts with fields that are unique per file storage."""
        new_files = [f for f in files if ("id" not in f)]
        new_files_by_storage = cls._group_file_data_by_file_storage(new_files)
        for file_storage, new_storage_files in new_files_by_storage.items():
            queryset = file_storage.files
            for field in file_storage.unique_file_fields_per_file_storage:
                cls._check_conflicts(
                    new_storage_files,
                    queryset=queryset,
                    field=field,
                    raise_exception=raise_exception,
                )
        return files

    @classmethod
    def _check_file_service_value_conflicts(cls, files: List[dict], raise_exception):
        """Check conflicts with fields that are unique per file service."""
        from apps.files.models import File

        new_files = [f for f in files if ("id" not in f) and (f["file_storage"] is not None)]
        new_files_by_service = cls._group_file_data_by_storage_service(new_files)
        for storage_service, new_service_files in new_files_by_service.items():
            proxy_model = cls.get_proxy_model(storage_service)
            queryset = File.objects.filter(file_storage__storage_service=storage_service)
            for field in proxy_model.unique_file_fields_per_storage_service:
                cls._check_conflicts(
                    new_service_files,
                    queryset=queryset,
                    field=field,
                    raise_exception=raise_exception,
                )
        return files

    @classmethod
    def check_file_data_conflicts(cls, files: List[dict], raise_exception=True) -> List[dict]:
        """Check values that should be unique for FileStorage or file service.

        Input Files are validated for required FileStorage fields based on
        storage_service value. When raise_exception is False and
        an error occurs, the error will be added to file['errors'] dict.

        Args:
            files: List of dicts containing file data
            raise_exception: Raise exception on error. Otherwise add errors to dict.

        Returns:
            files: File data with included errors.
        """
        files = cls._check_file_path_conflicts(files, raise_exception=raise_exception)
        files = cls._check_file_storage_value_conflicts(files, raise_exception=raise_exception)
        files = cls._check_file_service_value_conflicts(files, raise_exception=raise_exception)
        return files

    @classmethod
    def check_required_file_fields(cls, files: List[dict], raise_exception=True) -> List[dict]:
        """Check new file data for missing field values that are required by the FileStorage."""
        new_files = [f for f in files if ("id" not in f)]
        new_files_by_storage = cls._group_file_data_by_file_storage(new_files)
        for file_storage, storage_files in new_files_by_storage.items():
            required_fields = list(file_storage.required_file_fields)
            for file in storage_files:
                missing_fields = {field for field in required_fields if not file.get(field)}
                if missing_fields:
                    errors = {
                        field: _("Field is required for storage_service '{}'").format(
                            file_storage.storage_service
                        )
                        for field in missing_fields
                    }
                    if raise_exception:
                        raise ValidationError(errors)
                    file.setdefault("errors", {}).update(errors)

        return files


class BasicFileStorage(FileStorage):
    """FileStorage that does not support any extra fields."""

    class Meta:
        proxy = True


class ProjectFileStorage(FileStorage):
    """FileStorage that requires project_identifier to be set."""

    required_extra_fields = {"project_identifier"}

    class Meta:
        proxy = True


class IDAFileStorage(ProjectFileStorage):
    required_file_fields = {"file_storage_identifier"}

    class Meta:
        proxy = True
