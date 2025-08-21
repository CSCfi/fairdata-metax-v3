# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from typing import Iterable, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.helpers import get_attr_or_item, omit_empty
from apps.common.serializers.fields import ChecksumField, ListValidChoicesField
from apps.common.serializers.serializers import (
    CommonModelSerializer,
    CommonNestedModelSerializer,
    StrictSerializer,
)
from apps.files.helpers import get_file_metadata_serializer
from apps.files.models.file import File
from apps.files.models.file_characteristics import FileCharacteristics, FileFormatVersion
from apps.files.models.file_storage import FileStorage

from .fields import FileNameField, FilePathField

logger = logging.getLogger(__name__)


def get_or_create_storage(csc_project: str, storage_service: str) -> FileStorage:
    if storage_service not in settings.STORAGE_SERVICE_FILE_STORAGES:
        raise serializers.ValidationError(
            {
                "storage_service": _("Unknown storage service: '{storage_service}'").format(
                    storage_service=storage_service
                )
            }
        )
    storage, created = FileStorage.available_objects.get_or_create(
        csc_project=csc_project,
        storage_service=storage_service,
    )
    return storage


class CreateOnlyFieldsMixin:
    create_only_fields = []

    def update(self, instance, validated_data):
        for field in self.create_only_fields:
            if field in validated_data and getattr(instance, field) != validated_data[field]:
                raise serializers.ValidationError(
                    {field: "Changing field value after creation is not allowed"}
                )
        return super().update(instance, validated_data)


class FileCharacteristicsSerializer(CommonModelSerializer, StrictSerializer):
    file_format_version = FileFormatVersion.get_serializer_field(required=False, allow_null=True)
    encoding = ListValidChoicesField(
        choices=FileCharacteristics.EncodingChoices.choices, required=False, allow_null=True
    )
    csv_delimiter = ListValidChoicesField(
        choices=FileCharacteristics.CSVDelimiterChoices.choices, required=False, allow_null=True
    )
    csv_record_separator = ListValidChoicesField(
        choices=FileCharacteristics.CSVRecordSeparatorChoices.choices,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FileCharacteristics
        fields = [
            "file_format_version",
            "encoding",
            "csv_has_header",
            "csv_quoting_char",
            "csv_delimiter",
            "csv_record_separator",
        ]


class FileSerializer(CreateOnlyFieldsMixin, CommonNestedModelSerializer):
    create_only_fields = [
        "pathname",
        "csc_project",
        "storage_service",
        "storage_identifier",
    ]
    pas_only_fields = ["pas_compatible_file", "pas_process_running"]

    # FileStorage specific fields
    storage_service = ListValidChoicesField(choices=list(settings.STORAGE_SERVICE_FILE_STORAGES))
    csc_project = serializers.CharField(max_length=200, default=None)

    checksum = ChecksumField(max_length=200)

    # when saving files, filename and pathname are generated from pathname
    pathname = FilePathField()
    filename = FileNameField(read_only=True)

    dataset_metadata = serializers.SerializerMethodField()

    characteristics = FileCharacteristicsSerializer(required=False, allow_null=True)

    pas_process_running = serializers.BooleanField(required=False)

    non_pas_compatible_file = serializers.PrimaryKeyRelatedField(read_only=True)

    only_fields: Optional[Iterable] = None

    def __init__(self, *args, only_fields=None, **kwargs):
        self.only_fields = only_fields  # Allow restricting which fields are used
        super().__init__(*args, **kwargs)

    def get_fields(self):
        fields = super().get_fields()
        if self.only_fields is not None:
            fields = {name: fields[name] for name in self.only_fields}
        return fields

    def get_dataset_metadata(self, obj):
        if "file_metadata" in self.context:
            if metadata := self.context["file_metadata"].get(obj.id):
                return get_file_metadata_serializer()(metadata).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "file_metadata" not in self.context:
            rep.pop("dataset_metadata", None)

        storage = FileStorage.get_proxy_model(get_attr_or_item(instance, "storage_service"))
        storage.remove_unsupported_extra_fields(rep)
        return rep

    def to_internal_value(self, data):
        val = super().to_internal_value(data)

        # Fill identifying data for existing files.
        if self.instance:
            val.setdefault("id", self.instance.id)
            val.setdefault("storage_service", self.instance.storage.storage_service)
            val.setdefault("csc_project", self.instance.storage.csc_project)

        if not (self.parent and self.parent.many):
            # When in a list, this should be done in a parent serializer
            FileStorage.objects.assign_to_file_data(
                [val], allow_create=True, raise_exception=True, remove_filestorage_fields=True
            )
        return val

    def check_pas_field_permissions(self, instance: Optional[File], validated_data):
        user = self.context["request"].user
        if user.is_superuser or any(group.name == "pas" for group in user.groups.all()):
            return

        errors = {}
        for field in self.pas_only_fields:
            if field not in validated_data:
                continue

            if instance:
                if getattr(instance, field) != validated_data[field]:
                    errors[field] = "Only PAS service is allowed to set value."
            else:
                if validated_data[field]:  # Allow falsy values when creating
                    errors[field] = "Only PAS service is allowed to set value."

        if errors:
            raise serializers.ValidationError(errors)

    def create(self, validated_data):
        self.check_pas_field_permissions(instance=None, validated_data=validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if pas_compatible_file := validated_data.get("pas_compatible_file"):
            if pas_compatible_file.id == instance.id:
                raise serializers.ValidationError(
                    {"pas_compatible_file": "File cannot refer to itself."}
                )
        self.check_pas_field_permissions(instance=None, validated_data=validated_data)
        return super().update(instance, validated_data)

    def validate(self, data):
        if not (self.parent and self.parent.many):
            # When in a list, this should be done in a parent serializer
            FileStorage.check_required_file_fields([data], raise_exception=True)
            FileStorage.check_file_data_conflicts([data], raise_exception=True)

        return super().validate(data)

    class Meta:
        model = File
        fields = [
            "id",
            "storage_identifier",
            "pathname",
            "filename",
            "size",
            "storage_service",
            "csc_project",
            "checksum",
            "frozen",
            "modified",
            "removed",
            "published",
            "user",
            "dataset_metadata",
            "characteristics",
            "characteristics_extension",
            "pas_process_running",
            "pas_compatible_file",
            "non_pas_compatible_file",
        ]
        extra_kwargs = {"published": {"read_only": True}}
