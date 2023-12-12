"""Reference data fields listing

Helper script that prints a markdown table containing
fields that accept reference data.

Used for generating the table in `docs/user-guide/reference-data.md`.
"""

import os
import sys
from typing import Dict

import django

sys.path.append("./src")
os.environ["DJANGO_SETTINGS_MODULE"] = "metax_service.settings"
django.setup()

from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.actors.serializers import OrganizationSerializer
from apps.common.serializers import URLReferencedModelField, URLReferencedModelListField
from apps.core.serializers import (
    DataCatalogModelSerializer,
    DatasetSerializer,
    LicenseModelSerializer,
)
from apps.files.helpers import get_file_metadata_serializer
from apps.refdata.models import License
from apps.refdata.serializers import BaseRefdataSerializer


def get_url(serializer):
    model_name = serializer.Meta.model._meta.object_name.lower()
    return reverse(f"{model_name}-list")


extra_refdata_serializers = {
    OrganizationSerializer: reverse(f"organization-list"),
    LicenseModelSerializer: get_url(License.get_serializer_class()()),
}


def get_refdata_fields(serializer: serializers.Serializer, path="") -> Dict[str, str]:
    """Get mapping of field path -> reference data url."""
    nested_fields = {}

    def recurse(field, path=""):
        found = False
        for extra_serializer, serializer_url in extra_refdata_serializers.items():
            if isinstance(field, extra_serializer):
                nested_fields[path] = serializer_url
                found = True
                break
        if found:
            return
        elif isinstance(field, BaseRefdataSerializer):
            nested_fields[path] = get_url(field)
        elif isinstance(field, serializers.Serializer):
            for key, subfield in field.fields.items():
                key_path = key if path == "" else f"{path}.{key}"
                if isinstance(subfield, URLReferencedModelListField):
                    recurse(subfield.child, path=key_path + "[]")
                elif isinstance(subfield, URLReferencedModelField):
                    recurse(subfield.child, path=key_path)
                if isinstance(subfield, serializers.ListSerializer):
                    recurse(subfield.child, path=key_path + "[]")
                elif isinstance(subfield, serializers.Serializer):
                    recurse(subfield, path=key_path)

    recurse(serializer, path=path)
    return nested_fields


class DummyView:
    query_params = {}


context = {"view": DummyView()}

# map refdata field -> url
fields = {}
fields.update(get_refdata_fields(DatasetSerializer(context=context), path="Dataset"))
fields.update(get_refdata_fields(DataCatalogModelSerializer(context=context), path="DataCatalog"))
# File.dataset_metadata is a SerializerMethodField so it doesn't get handled automatically
fields.update(
    get_refdata_fields(
        get_file_metadata_serializer()(context=context), path="File.dataset_metadata"
    )
)

# map refdata url -> field
refdata_fields = {}
for field, path in fields.items():
    refdata_fields.setdefault(path, []).append(field)

refdata_fields = {key: refdata_fields[key] for key in sorted(refdata_fields)}


print("<!-- table generated with refdata_fields.py -->")
print("")
print("| Reference data | Used by fields |")
print("|---|---|")
for url, fields in refdata_fields.items():
    print(f"| `{url}` | {'<br>'.join(sorted(fields))} |")
