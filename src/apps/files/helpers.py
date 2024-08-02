import copy
from typing import Optional
from urllib import parse

from django.conf import settings
from django.utils.module_loading import import_string

from apps.common.helpers import ensure_dict


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


def convert_checksum_v2_to_v3(checksum: dict, value_key="value") -> Optional[str]:
    if not checksum:
        return None
    ensure_dict(checksum)
    algorithm = checksum.get("algorithm", "").lower().replace("-", "")
    value = checksum.get(value_key, "").lower()
    return f"{algorithm}:{value}"


def convert_checksum_v3_to_v2(checksum: str) -> Optional[dict]:
    if not checksum:
        return None

    try:
        algo, value = checksum.split(":", maxsplit=1)
    except ValueError:
        algo = None
        value = checksum

    v2_algos = {
        "md5": "MD5",
        "sha1": "SHA-1",
        "sha224": "SHA-224",
        "sha256": "SHA-384",
        "sha512": "SHA-512",
    }
    v2_algo = v2_algos.get(algo, "OTHER")
    return {
        "checksum_value": value,
        "algorithm": v2_algo,
    }
