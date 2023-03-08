# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

logger = logging.getLogger(__name__)


class URLReferencedModelListField(serializers.ListField):
    """Custom serializer for a model list.

    Allows user to represent targets using the 'url' key.

    The 'child' parameter in 'serializers.ListField' is used for serializing
    the list in the response.
    """

    def to_representation(self, manager):
        return [self.child.to_representation(entry) for entry in manager.all()]

    def to_internal_value(self, data):
        if not isinstance(data, list) or isinstance(data, (str, dict)):
            self.fail("not_a_list", input_type=type(data).__name__)

        if data and hasattr(data[0], "url"):
            # The list of entries has already been converted into model
            # instances
            return data

        try:
            urls = set(entry["url"] for entry in data)
        except KeyError:
            raise serializers.ValidationError(
                "'url' field must be defined for each object in the list"
            )
        except TypeError:
            raise serializers.ValidationError(
                "Each item in the list must be an object with the field 'url'"
            )

        model = self.child.Meta.model
        entries = list(model.objects.filter(url__in=urls))

        retrieved_urls = set(entry.url for entry in entries)
        missing_urls = urls - retrieved_urls

        if missing_urls:
            raise serializers.ValidationError(
                "Entries not found for given URLs: {}".format(", ".join(missing_urls))
            )

        return entries


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
