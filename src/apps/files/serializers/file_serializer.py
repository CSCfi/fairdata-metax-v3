# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.conf import settings
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.helpers import get_attr_or_item
from apps.files.helpers import get_file_metadata_serializer
from apps.files.models.file import File, FileStorage, checksum_algorithm_choices
from apps.files.models.file_storage import FileStorage

from .fields import (
    DirectoryPathField,
    FileNameField,
    FilePathField,
    ListValidChoicesField,
    StorageServiceField,
)

logger = logging.getLogger(__name__)


def get_or_create_file_storage(project_identifier: str, storage_service: str) -> FileStorage:
    if storage_service not in settings.STORAGE_SERVICE_FILE_STORAGES:
        raise serializers.ValidationError(
            {
                "storage_service": _("Unknown storage service: '{storage_service}'").format(
                    storage_service=storage_service
                )
            }
        )
    storage, created = FileStorage.available_objects.get_or_create(
        project_identifier=project_identifier,
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


class ChecksumSerializer(serializers.Serializer):
    algorithm = ListValidChoicesField(choices=checksum_algorithm_choices)
    checked = serializers.DateTimeField()
    value = serializers.CharField()


class FileSerializer(CreateOnlyFieldsMixin, serializers.ModelSerializer):
    create_only_fields = [
        "file_path",
        "project_identifier",
        "storage_service",
        "file_storage_identifier",
        "file_storage_pathname",
    ]

    # FileStorage specific fields
    storage_service = ListValidChoicesField(choices=list(settings.STORAGE_SERVICE_FILE_STORAGES))
    project_identifier = serializers.CharField(max_length=200, default=None)

    checksum = ChecksumSerializer()

    # when saving files, file_name and directory_path are generated from file_path
    file_path = FilePathField()
    file_name = FileNameField(read_only=True)
    directory_path = DirectoryPathField(read_only=True)

    dataset_metadata = serializers.SerializerMethodField()

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

        # FileStorage validation expects id in data for existing files.
        if self.instance:
            val.setdefault("id", self.instance.id)

        if not (self.parent and self.parent.many):
            # When in a list, this should be done in a parent serializer
            FileStorage.objects.assign_to_file_data(
                [val], allow_create=True, raise_exception=True, remove_filestorage_fields=True
            )
        return val

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
            "file_path",
            "file_name",
            "directory_path",
            "byte_size",
            "storage_service",
            "project_identifier",
            "file_storage_identifier",
            "file_storage_pathname",
            "checksum",
            "date_frozen",
            "file_modified",
            "date_uploaded",
            "created",
            "modified",
            "dataset_metadata",
        ]

    # TODO: Partial update


class DeleteWithProjectIdentifierSerializer(serializers.Serializer):
    storage_service = StorageServiceField(required=True)
    project_identifier = serializers.CharField(max_length=200, required=True)
    flush = serializers.BooleanField(required=False, default=False)
    deleted_files_count = serializers.JSONField(required=False, read_only=True)

    def delete_project(self):
        validated_data = self.validated_data
        query: QuerySet
        if validated_data["flush"]:
            query = File.all_objects.filter(
                file_storage__project_identifier=validated_data["project_identifier"],
                file_storage__storage_service=validated_data["storage_service"],
            )
        else:
            query = File.available_objects.filter(
                file_storage__project_identifier=validated_data["project_identifier"],
                file_storage__storage_service=validated_data["storage_service"],
            )
        logger.info(f"Deleting {query=}")
        self.validated_data["deleted_files_count"] = query.count()
        query.delete()
