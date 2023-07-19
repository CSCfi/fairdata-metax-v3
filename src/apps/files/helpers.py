import copy
from urllib import parse

from django.conf import settings
from django.utils.module_loading import import_string


def remove_query_param(url, *params):
    """Remove parameter from query string."""
    split = parse.urlsplit(url)._asdict()
    query = parse.parse_qs(split["query"])
    for param in params:
        query.pop(param, None)
    split["query"] = parse.urlencode(query, doseq=True, safe="/:")
    new_url = parse.urlunsplit(split.values())
    return new_url


def replace_query_param(url, param, value):
    """Set parameter value in query string."""
    split = parse.urlsplit(url)._asdict()
    query = parse.parse_qs(split["query"])
    query[param] = value
    split["query"] = parse.urlencode(query, doseq=True, safe="/:")
    new_url = parse.urlunsplit(split.values())
    return new_url


def replace_query_path(url, path):
    """Replace path query paremeter, clear pagination offset"""
    url = remove_query_param(url, "offset")
    return replace_query_param(url, param="path", value=path)


def remove_hidden_fields(fields, visible):
    """If 'visible' iterable is set, remove fields that are not listed in 'visible'."""
    fields = copy.copy(fields)
    if visible is not None and fields is not None:
        for field_name in set(fields) - set(visible):
            fields.pop(field_name)
    return fields


# Helpers for getting File and Directory metadata models and serializers
# from configuration instead of importing them directly from another app.


def get_file_metadata_model():
    return import_string(settings.DATASET_FILE_METADATA_MODELS["file"])


def get_directory_metadata_model():
    return import_string(settings.DATASET_FILE_METADATA_MODELS["directory"])


def get_file_metadata_serializer():
    return import_string(settings.DATASET_FILE_METADATA_SERIALIZERS["file"])


def get_directory_metadata_serializer():
    return import_string(settings.DATASET_FILE_METADATA_SERIALIZERS["directory"])
