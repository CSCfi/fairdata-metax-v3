# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import SkipField, empty

logger = logging.getLogger(__name__)


class AbstractDatasetModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        abstract = True


class AbstractDatasetPropertyModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("id", "url", "title")
        abstract = True

    def to_representation(self, instance):
        if isinstance(instance.title, str):
            instance.title = json.loads(instance.title)
        representation = super().to_representation(instance)

        return representation

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        if "id" in data:
            try:
                UUID(data.get("id"))
                internal_value["id"] = data.get("id")
            except ValueError:
                raise serializers.ValidationError(
                    _("id: {} is not valid UUID").format(data.get("id"))
                )

        return internal_value


class CommonListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        # Map the instance objects by their unique identifiers
        instance_mapping = {obj.id: obj for obj in instance}
        updated_instances = []

        # Perform updates or create new instances
        for item_data in validated_data:
            item_id = item_data.get("id", None)
            if item_id is not None:
                # Update the existing instance
                item_instance = instance_mapping.get(item_id, None)
                if item_instance is not None:
                    item_serializer = self.child._default_class(data=item_data)
                    item_serializer.is_valid(raise_exception=True)
                    updated_instances.append(item_serializer.update(item_instance, item_data))
            else:
                # Create a new instance
                item_serializer = self.child.create(item_data)
                updated_instances.append(item_serializer)

        # Delete instances that were not included in the update
        for item in instance:
            if item.id not in [item_data.get("id", None) for item_data in validated_data]:
                item.delete()

        return updated_instances


class StrictSerializer(serializers.Serializer):
    """Serializer that throws an error for unknown fields."""

    def to_internal_value(self, data):
        if unknown_fields := set(data).difference(self.fields):
            raise serializers.ValidationError(
                {field: _("Unknown field") for field in unknown_fields}
            )
        return super().to_internal_value(data)


class PatchSerializer(serializers.Serializer):
    """Serializer which allows partial update that does not propagate to nested serializers.

    For partial updates, use patch=True which does not make nested updates partial.
    Using partial=True throws a ValueError to prevent accidentally using the
    default (propagating) partial update style.
    """

    def __init__(self, *args, **kwargs):
        self.patch = kwargs.pop("patch", False)
        if kwargs.get("partial"):
            raise ValueError(
                "PatchSerializer should not be used with partial=True. Use patch=True instead."
            )
        super().__init__(*args, **kwargs)

    def get_fields(self):
        """When patch is enabled, no fields are required."""
        fields = super().get_fields()
        if self.patch:
            for field in fields.values():
                field.required = False
                if not field.read_only:
                    field.default = empty
        return fields
