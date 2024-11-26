# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from uuid import UUID

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import ListValidChoicesField


class FileNameField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected file name to not contain slashes.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(filename_regex, *args, **kwargs)

    class Meta:
        swagger_schema_fields = {"example": "file.txt"}


class FilePathField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected file path to be in format '/path/file'.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(file_pathname_regex, *args, **kwargs)

    class Meta:
        swagger_schema_fields = {"example": "/path/file.txt"}


class DirectoryPathField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected directory path to be in format /path/.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(directory_pathname_regex, *args, **kwargs)

    class Meta:
        swagger_schema_fields = {"example": "/path/"}


class OptionalSlashDirectoryPathField(serializers.RegexField):
    """Directory path field that automatically appends slash to end if missing."""

    default_error_messages = {
        "invalid": _("Expected directory path to be in format /path/ or /path.")
    }

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(optional_slash_pathname_regex, *args, **kwargs)

    def to_internal_value(self, data):
        if data and not data.endswith("/"):
            data += "/"
        return super().to_internal_value(data)


class StorageServiceField(ListValidChoicesField):
    """ChoiceField with validation for storage services."""

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = list(settings.STORAGE_SERVICE_FILE_STORAGES)
        super().__init__(*args, **kwargs)


filename_regex = r"^[^/]+$"  # e.g. file
file_pathname_regex = r"^/([^/]+/)*[^/]+$"  # e.g. /directory/subdirectory/file
directory_pathname_regex = r"^/([^/]+/)*$"  # e.g. /directory/subdirectory/
optional_slash_pathname_regex = (
    r"^/([^/]+/?)*$"  # e.g. /directory/subdirectory/ or /directory/subdirectory
)


class PrimaryKeyRelatedOrUUIDField(serializers.PrimaryKeyRelatedField):
    """PrimaryKeyRelated field that supports UUID instances when serializing.

    Normally related instance is a model instance but when using .values(),
    the instance is just the primary key."""

    def to_representation(self, value):
        if isinstance(value, UUID):
            return value
        return super().to_representation(value)
