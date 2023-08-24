# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from rest_framework import serializers

from apps.files.helpers import (
    get_directory_metadata_serializer,
    remove_hidden_fields,
    replace_query_path,
)
from apps.files.models.file import FileStorage
from apps.files.serializers.file_serializer import FileSerializer


class ContextFileStorageMixin(serializers.Serializer):
    """Serializer mixin that gets FileStorage fields from context."""

    storage_service = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    def get_storage(self, obj) -> FileStorage:
        return self.context.get("storage")

    def get_project(self, obj):
        if "storage" in self.context:
            return self.context["storage"].project

    def get_storage_service(self, obj):
        if "storage" in self.context:
            return self.context["storage"].storage_service


class DirectoryFileSerializer(ContextFileStorageMixin, FileSerializer):
    def get_fields(self):
        fields = super().get_fields()
        return remove_hidden_fields(fields, self.context.get("file_fields"))


class BaseDirectorySerializer(ContextFileStorageMixin, serializers.Serializer):
    name = serializers.CharField()
    pathname = serializers.CharField()
    file_count = serializers.IntegerField()  # total file count including subdirectories
    size = serializers.IntegerField()  # total byte size including subdirectories
    created = serializers.DateTimeField(default=None)  # oldest file modification
    modified = serializers.DateTimeField(default=None)  # most recent file modification

    dataset_metadata = serializers.SerializerMethodField(read_only=True)

    def get_dataset_metadata(self, obj):
        if "directory_metadata" in self.context:
            if metadata := self.context["directory_metadata"].get(obj["pathname"]):
                return get_directory_metadata_serializer()(metadata).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "directory_metadata" not in self.context:
            rep.pop("dataset_metadata", None)

        # FileStorage should be available in context for directories
        if storage := self.get_storage(instance):
            storage.remove_unsupported_extra_fields(rep)
        return rep


class SubDirectorySerializer(BaseDirectorySerializer):
    """Serializer for subdirectory, shows file counts and sizes."""

    url = serializers.SerializerMethodField(read_only=True, method_name="get_url")

    def get_fields(self):
        fields = super().get_fields()
        return remove_hidden_fields(fields, self.context.get("directory_fields"))

    def get_url(self, obj):
        """Get url for browsing directory contents."""
        url = self.context["request"].build_absolute_uri()
        new_url = replace_query_path(url, obj["pathname"])
        return new_url


class ParentDirectorySerializer(BaseDirectorySerializer):
    parent_url = serializers.SerializerMethodField(read_only=True, method_name="get_parent_url")

    def get_parent_url(self, obj):
        """Get url for navigating to parent of current directory."""
        if obj["pathname"] == "/":
            return None
        url = self.context["request"].build_absolute_uri()
        parent_path = "/".join(obj["pathname"].split("/")[:-2]) + "/"
        new_url = replace_query_path(url, parent_path)
        return new_url


class DirectorySerializer(serializers.Serializer):
    """Serializer for directory with subdirectories and files."""

    directory = ParentDirectorySerializer(default=None)  # directory being viewed
    directories = SubDirectorySerializer(many=True)  # direct child directories
    files = DirectoryFileSerializer(many=True)  # direct child files

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["directory"] is None:
            del data["directory"]
        return data
