# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging

from django.core.validators import EMPTY_VALUES
from rest_framework import serializers

from apps.actors.serializers import ActorModelSerializer
from apps.common.helpers import update_or_create_instance
from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
)
from apps.core.models import (
    AccessRights,
    CatalogHomePage,
    DatasetActor,
    DatasetPublisher,
    MetadataProvider,
    Spatial,
)
from apps.core.models.concepts import AccessType, DatasetLicense
from apps.refdata import models as refdata
from apps.users.serializers import MetaxUserModelSerializer

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

    description = serializers.JSONField(required=False)
    url = serializers.URLField(required=False)
    pref_label = serializers.HStoreField(read_only=True)
    in_scheme = serializers.URLField(max_length=255, read_only=True)
    broader = refdata.License.get_serializer()(many=True, read_only=True)
    same_as = refdata.License.get_serializer()(many=True, read_only=True)

    class Meta:
        model = DatasetLicense
        fields = [
            "custom_url",
            "description",
            "url",
            "pref_label",
            "in_scheme",
            "broader",
            "same_as",
        ]

        ref_name = "DatasetLicense"

    def create(self, validated_data):
        reference: refdata.License
        custom_url = validated_data.get("custom_url")
        url = validated_data.pop("url", None)

        if url is None and custom_url is None:
            raise serializers.ValidationError(detail="License needs url or custom_url, got None")

        if url is None:
            url = "http://uri.suomi.fi/codelist/fairdata/license/code/other"

        try:
            reference = refdata.License.objects.get(url=url)
        except refdata.License.DoesNotExist:
            raise serializers.ValidationError(detail=f"License not found {url}")

        return DatasetLicense.objects.create(**validated_data, reference=reference)

    def update(self, instance, validated_data):
        url = validated_data.pop("url", instance.reference.url)

        if url != instance.reference.url:
            try:
                instance.reference = refdata.License.objects.get(url=url)
            except refdata.License.DoesNotExist:
                raise serializers.ValidationError(detail=f"License not found {url}")

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        refdata_serializer = refdata.License.get_serializer()
        serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}


class SpatialModelSerializer(serializers.ModelSerializer):
    """Custom serializer for License that does not require pref_label

    Conforms use case where AccessRights object can be created with only url-field in license

    """

    class Meta:
        model = Spatial
        fields = [
            "url",
            "pref_label",
            "in_scheme",
            "full_address",
            "geographic_name",
            "altitude_in_meters",
            "dataset",
            "provenance",
        ]

    def create(self, validated_data):
        reference: refdata.Location
        url = validated_data.pop("url", None)

        if not url:
            raise serializers.ValidationError("Spatial needs url, got None")

        try:
            reference = refdata.Location.objects.get(url=url)
        except refdata.Location.DoesNotExist:
            raise serializers.ValidationError(f"Location not found {url}")

        return Spatial.objects.create(**validated_data, reference=reference)

    def update(self, instance, validated_data):
        url = validated_data.pop("url", instance.url)

        if url != instance.url:
            try:
                instance.reference = refdata.Location.objects.get(url=url)
            except refdata.Location.DoesNotExist:
                raise serializers.ValidationError(detail=f"Location not found {url}")

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        refdata_serializer = refdata.Location.get_serializer()
        serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = LicenseModelSerializer(read_only=False, required=False, many=True)
    access_type = AccessType.get_serializer()(required=False, read_only=False, many=False)
    description = serializers.JSONField(required=False)

    class Meta:
        model = AccessRights
        fields = ("id", "description", "license", "access_type")

    def create(self, validated_data):
        license_serializer: LicenseModelSerializer = self.fields["license"]
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))

        license_data = validated_data.pop("license", [])
        licenses = license_serializer.create(license_data)

        access_rights = AccessRights.objects.create(access_type=access_type, **validated_data)
        access_rights.license.set(licenses)

        return access_rights

    def update(self, instance, validated_data):
        license_serializer: LicenseModelSerializer = self.fields["license"]
        access_type = None
        access_type_data = validated_data.pop("access_type", None)
        if access_type_data not in EMPTY_VALUES:
            access_type = AccessType.objects.get(url=access_type_data.get("url"))
        instance.access_type = access_type

        license_data = validated_data.pop("license", [])
        licenses = license_serializer.create(license_data)
        instance.license.set(licenses)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        if isinstance(instance.description, str):
            instance.description = json.loads(instance.description)
        representation = super().to_representation(instance)

        return representation


class DatasetActorModelSerializer(serializers.ModelSerializer):
    actor = ActorModelSerializer(required=True, many=False)

    def create(self, validated_data):
        actor = None
        if actor_data := validated_data.pop("actor", None):
            actor = self.fields["actor"].create(actor_data)

        return DatasetActor.objects.create(**validated_data, actor=actor)

    class Meta:
        model = DatasetActor
        fields = ("id", "role", "actor")


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
