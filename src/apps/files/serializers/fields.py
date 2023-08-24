# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import to_choices_dict


class CommaSeparatedListField(serializers.ListField):
    """ListField that serializes into a comma-separated string."""

    def get_value(self, dictionary):
        return super(serializers.ListField, self).get_value(dictionary)

    def to_internal_value(self, data):
        data = data.split(",")
        return super().to_internal_value(data)

    def to_representation(self, data):
        return ",".join(data)


class ListValidChoicesField(serializers.ChoiceField):
    """ChoiceField that lists valid choices in the 'invalid choice' error message."""

    def __init__(self, *args, **kwargs):
        choices = kwargs.get("choices", [])
        kwargs["error_messages"] = {
            "invalid_choice": serializers.ChoiceField.default_error_messages["invalid_choice"]
            + " "
            + _("Valid choices are: {choices}").format(
                choices=[c for c in to_choices_dict(choices)]
            ),
            **kwargs.get("error_messages", {}),
        }

        super().__init__(*args, **kwargs)


filename_regex = r"^[^/]+$"  # e.g. file
file_pathname_regex = r"^/([^/]+/)*[^/]+$"  # e.g. /directory/subdirectory/file
directory_pathname_regex = r"^/([^/]+/)*$"  # e.g. /directory/subdirectory/
optional_slash_pathname_regex = (
    r"^/([^/]+/?)*$"  # e.g. /directory/subdirectory/ or /directory/subdirectory
)


class FileNameField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected file name to not contain slashes.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(filename_regex, *args, **kwargs)


class FilePathField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected file path to be in format '/path/file'.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(file_pathname_regex, *args, **kwargs)


class DirectoryPathField(serializers.RegexField):
    default_error_messages = {"invalid": _("Expected directory path to be in format /path/.")}

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(directory_pathname_regex, *args, **kwargs)


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
