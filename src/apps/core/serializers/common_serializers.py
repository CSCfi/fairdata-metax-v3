# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging

from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.helpers import update_or_create_instance
from apps.core.models import (
    CatalogHomePage,
    DatasetPublisher,
    AccessRights,
    MetadataProvider,
)
from apps.core.models.concepts import License, AccessType
from apps.users.models import MetaxUser
from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
    URLReferencedModelListField,
)

logger = logging.getLogger(__name__)


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


class LicenseModelSerializer(serializers.ModelSerializer):
    """Custom serializer for License that does not require pref_label

    Conforms use case where AccessRights object can be created with only url-field in license

    """

    class Meta:
        model = License
        ref_name = "CustomLicenseModelSerializer"
        fields = ("url",)


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = URLReferencedModelListField(
        child=LicenseModelSerializer(required=False), read_only=False, required=False
    )
    access_type = AccessType.get_serializer()(required=False, read_only=False, many=False)
    description = serializers.JSONField(required=False)

    class Meta:
        model = AccessRights
        fields = ("id", "description", "license", "access_type")

    def create(self, validated_data):
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))

        licenses = validated_data.pop("license", [])

        access_rights = AccessRights.objects.create(access_type=access_type, **validated_data)
        access_rights.license.set(licenses)

        return access_rights

    def update(self, instance, validated_data):
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))
        instance.access_type = access_type

        licenses = validated_data.pop("license", [])
        instance.license.set(licenses)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        if isinstance(instance.description, str):
            instance.description = json.loads(instance.description)
        representation = super().to_representation(instance)

        return representation


class MetaxUserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaxUser
        fields = ("id", "username", "email", "first_name", "last_name")


class MetadataProviderModelSerializer(AbstractDatasetModelSerializer):
    user = MetaxUserModelSerializer()

    class Meta:
        model = MetadataProvider
        fields = ("id", "user", "organization")

    def create(self, validated_data):
        user = None

        user_serializer: MetaxUserModelSerializer = self.fields["user"]

        if user_data := validated_data.pop("user", None):
            user = user_serializer.create(user_data)

        new_metadata_provider: MetadataProvider = MetadataProvider.objects.create(
            user=user, **validated_data
        )

        return new_metadata_provider

    def update(self, instance, validated_data):
        user_serializer = self.fields["user"]
        user_instance = instance.user

        if user_data := validated_data.pop("user", None):
            update_or_create_instance(user_serializer, user_instance, user_data)

        return super().update(instance, validated_data)
