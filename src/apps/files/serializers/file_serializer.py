# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from collections import Counter
from dataclasses import dataclass

from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.files.helpers import get_file_metadata_serializer
from apps.files.models.file import File, StorageProject, checksum_algorithm_choices
from apps.files.models.file_storage import FileStorage

from .fields import DirectoryPathField, FileNameField, FilePathField, ListValidChoicesField


def get_storage_project_or_none(project_identifier, file_storage_id):
    try:
        project = StorageProject.available_objects.get(
            project_identifier=project_identifier,
            file_storage_id=file_storage_id,
        )
        return project
    except StorageProject.DoesNotExist:
        return None


def get_or_create_storage_project(project_identifier, file_storage_id) -> StorageProject:
    try:
        project, created = StorageProject.available_objects.get_or_create(
            project_identifier=project_identifier,
            file_storage=FileStorage.available_objects.get(id=file_storage_id),
        )
    except FileStorage.DoesNotExist:
        raise serializers.ValidationError(
            {
                "file_storage": _("File storage not found: '{storage_id}'").format(
                    storage_id=file_storage_id
                )
            }
        )
    return project


def validate_path_conflicts(storage_project, file_paths):
    """Validate file paths for uniqueness conflicts."""
    repeated = [path for path, count in Counter(file_paths).items() if count > 1]
    if len(repeated) > 0:
        raise serializers.ValidationError(
            {
                "file_path": _("Cannot create multiple files with same path: {paths}").format(
                    paths=repeated
                )
            }
        )

    if storage_project is None:
        return

    conflicts = (
        File.objects.filter(
            storage_project=storage_project,
            # prefilter results before doing a more expensive exact match with Concat
            directory_path__in=set(p.rsplit("/", 1)[0] + "/" for p in file_paths),
            file_name__in=set(p.rsplit("/", 1)[1] for p in file_paths),
        )
        .annotate(file_path=Concat("directory_path", "file_name"))
        .filter(
            file_path__in=file_paths,
        )
        .values_list("file_path", flat=True)
    )
    if conflicts:
        raise serializers.ValidationError(
            {
                "file_path": _("File with path already exists: {paths}").format(
                    paths=list(conflicts)
                )
            }
        )


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
    create_only_fields = ["file_path", "project_identifier", "file_storage"]

    project_identifier = serializers.CharField(max_length=200)
    file_storage = serializers.CharField(max_length=255, source="file_storage.id")

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
        return rep

    def validate(self, data):
        if not (self.parent and self.parent.many):
            if storage_project := get_storage_project_or_none(
                project_identifier=data["project_identifier"],
                file_storage_id=data["file_storage"]["id"],
            ):
                validate_path_conflicts(
                    storage_project=storage_project,
                    file_paths=[data["file_path"]],
                )

        return super().validate(data)

    class Meta:
        model = File
        fields = [
            "id",
            "file_path",
            "file_name",
            "directory_path",
            "byte_size",
            "project_identifier",
            "file_storage",
            "checksum",
            "date_frozen",
            "file_modified",
            "date_uploaded",
            "created",
            "modified",
            "dataset_metadata",
        ]

    def create(self, validated_data):
        project_identifier = validated_data.pop("project_identifier", None)
        file_storage = validated_data.pop("file_storage", {}).get("id")

        project_id = get_or_create_storage_project(project_identifier, file_storage).id
        validated_data["storage_project_id"] = project_id
        return super().create(validated_data)

    # TODO: Partial update
