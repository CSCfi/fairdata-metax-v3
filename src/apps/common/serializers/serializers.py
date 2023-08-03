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
