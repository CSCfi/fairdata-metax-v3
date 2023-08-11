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
