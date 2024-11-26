# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.common.serializers import CommonNestedModelSerializer
from apps.common.serializers.fields import NoopField
from apps.core.models import DataCatalog, Language
from apps.core.serializers import DatasetPublisherModelSerializer

logger = logging.getLogger(__name__)


class GetOrCreateGroupField(serializers.SlugRelatedField):
    """Group serializer field that creates Group if it does not exist."""

    def __init__(self, **kwargs):
        kwargs["slug_field"] = "name"
        kwargs["queryset"] = Group.objects.all()
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            group, created = queryset.get_or_create(**{self.slug_field: data})
            return group
        except (TypeError, ValueError):
            self.fail("invalid")


class DataCatalogModelSerializer(CommonNestedModelSerializer):
    publisher = DatasetPublisherModelSerializer(required=False)
    language = Language.get_serializer_field(required=False, many=True)
    dataset_groups_create = GetOrCreateGroupField(required=False, many=True)
    dataset_groups_admin = GetOrCreateGroupField(required=False, many=True)
    harvested = NoopField(help_text="No longer in use. Replaced by is_external.")

    class Meta:
        model = DataCatalog
        fields = (
            "id",
            "description",
            "publisher",
            "logo",
            "language",
            "title",
            "dataset_versioning_enabled",
            "is_external",
            "harvested",
            "dataset_groups_create",
            "dataset_groups_admin",
            "allow_remote_resources",
            "storage_services",
            "publishing_channels",
            "allowed_pid_types",
            "rems_enabled",
        )

    def update(self, instance, validated_data):
        if "id" in validated_data and validated_data["id"] != instance.id:
            raise serializers.ValidationError(
                {"id": "Value cannot be changed for an existing data catalog."}
            )
        return super().update(instance, validated_data)
