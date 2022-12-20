# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging

from uuid import UUID

from django.core.validators import EMPTY_VALUES
from rest_framework import serializers

from apps.core.models import (
    CatalogHomePage,
    DatasetPublisher,
    AccessRights,
)
from apps.core.models.concepts import License, AccessType


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
                    "id: {} is not a valid UUID".format(data.get("id"))
                )

        return internal_value


class CatalogHomePageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = CatalogHomePage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields


class DatasetPublisherModelSerializer(AbstractDatasetModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("id", "name", "homepage")

    def create(self, validated_data):
        homepages = validated_data.pop("homepage")
        dataset_publisher = DatasetPublisher.objects.create(**validated_data)
        pages = []
        for page in homepages:
            page_created = CatalogHomePage.objects.create(**page)
            pages.append(page_created)
        dataset_publisher.homepage.set(pages)
        return dataset_publisher

    def update(self, instance, validated_data):
        homepages = validated_data.pop("homepage")
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        pages = []
        for homepage in homepages:
            page, created = CatalogHomePage.objects.update_or_create(
                id=homepage.get("id"), defaults=homepage
            )
            pages.append(page)
        instance.homepage.set(pages)
        return instance

    def to_representation(self, instance):
        logger.info(f"{instance.name=}")
        if isinstance(instance.name, str):
            instance.name = json.loads(instance.name)
        representation = super().to_representation(instance)

        return representation


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = License.get_serializer()(required=False, read_only=False, many=True)
    access_type = AccessType.get_serializer()(
        required=False, read_only=False, many=False
    )
    description = serializers.JSONField(required=False)

    class Meta:
        model = AccessRights
        fields = ("id", "description", "license", "access_type")

    def create(self, validated_data):
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))

        license_data = validated_data.pop("license", [])
        licenses = [
            License.objects.get(url=license.get("url")) for license in license_data
        ]

        access_rights = AccessRights.objects.create(
            access_type=access_type, **validated_data
        )
        access_rights.license.set(licenses)

        return access_rights

    def update(self, instance, validated_data):
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))
        instance.access_type = access_type

        license_data = validated_data.pop("license", [])
        licenses = [
            License.objects.get(url=license.get("url")) for license in license_data
        ]
        instance.license.set(licenses)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        if isinstance(instance.description, str):
            instance.description = json.loads(instance.description)
        representation = super().to_representation(instance)

        return representation
