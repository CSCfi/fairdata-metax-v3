# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from rest_framework import serializers

from apps.files.helpers import remove_hidden_fields, replace_query_path

from .file_serializer import FileSerializer


class ContextStorageProjectMixin(serializers.Serializer):
    """Serializer mixin that gets StorageProject fields from context."""

    file_storage = serializers.SerializerMethodField()
    project_identifier = serializers.SerializerMethodField()

    def get_project_identifier(self, obj):
        if "storage_project" in self.context:
            return self.context["storage_project"].project_identifier

    def get_file_storage(self, obj):
        if "storage_project" in self.context:
            return self.context["storage_project"].file_storage_id


class DirectoryFileSerializer(ContextStorageProjectMixin, FileSerializer):
    def get_fields(self):
        fields = super().get_fields()
        return remove_hidden_fields(fields, self.context.get("file_fields"))


class BaseDirectorySerializer(ContextStorageProjectMixin, serializers.Serializer):
    directory_name = serializers.CharField()
    directory_path = serializers.CharField()
    file_count = serializers.IntegerField()  # total file count including subdirectories
    byte_size = serializers.IntegerField()  # total byte size including subdirectories
    created = serializers.DateTimeField(default=None)  # first file creation time
    modified = serializers.DateTimeField(default=None)  # most recent file modification


class SubDirectorySerializer(BaseDirectorySerializer):
    """Serializer for subdirectory, shows file counts and sizes."""

    url = serializers.SerializerMethodField(read_only=True, method_name="get_url")

    def get_fields(self):
        fields = super().get_fields()
        return remove_hidden_fields(fields, self.context.get("directory_fields"))

    def get_url(self, obj):
        """Get url for browsing directory contents."""
        url = self.context["request"].build_absolute_uri()
        new_url = replace_query_path(url, obj["directory_path"])
        return new_url


class ParentDirectorySerializer(BaseDirectorySerializer):
    parent_url = serializers.SerializerMethodField(read_only=True, method_name="get_parent_url")

    def get_parent_url(self, obj):
        """Get url for navigating to parent of current directory."""
        if obj["directory_path"] == "/":
            return None
        url = self.context["request"].build_absolute_uri()
        parent_path = "/".join(obj["directory_path"].split("/")[:-2]) + "/"
        new_url = replace_query_path(url, parent_path)
        return new_url


class DirectorySerializer(serializers.Serializer):
    """Serializer for directory with subdirectories and files."""

    parent_directory = ParentDirectorySerializer(default=None)  # directory being viewed
    directories = SubDirectorySerializer(many=True)  # direct child directories
    files = DirectoryFileSerializer(many=True)  # direct child files

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["parent_directory"] is None:
            del data["parent_directory"]
        return data
