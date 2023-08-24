# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import json
import logging

from django.contrib.auth import get_user_model
from django.core.validators import EMPTY_VALUES
from rest_framework import serializers
from rest_framework.fields import empty

from apps.actors.serializers import ActorModelSerializer
from apps.common.helpers import update_or_create_instance
from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
    CommonListSerializer,
)
from apps.core.models import (
    AccessRights,
    CatalogHomePage,
    DatasetActor,
    DatasetPublisher,
    MetadataProvider,
    OtherIdentifier,
)
from apps.core.models.concepts import AccessType, DatasetLicense, IdentifierType, License
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
    same_as = License.get_serializer_field(many=True, read_only=True)

    class Meta:
        model = DatasetLicense
        fields = [
            "custom_url",
            "description",
            "url",
            "pref_label",
            "in_scheme",
            "same_as",
        ]

        ref_name = "DatasetLicense"

    def create(self, validated_data):
        reference: License
        custom_url = validated_data.get("custom_url")
        url = validated_data.pop("url", None)

        if url is None and custom_url is None:
            raise serializers.ValidationError(detail="License needs url or custom_url, got None")

        if url is None:
            url = "http://uri.suomi.fi/codelist/fairdata/license/code/other"

        try:
            reference = License.objects.get(url=url)
        except License.DoesNotExist:
            raise serializers.ValidationError(detail=f"License not found {url}")

        return DatasetLicense.objects.create(**validated_data, reference=reference)

    def update(self, instance, validated_data):
        url = validated_data.pop("url", instance.reference.url)

        if url != instance.reference.url:
            try:
                instance.reference = License.objects.get(url=url)
            except License.DoesNotExist:
                raise serializers.ValidationError(detail=f"License not found {url}")

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        refdata_serializer = License.get_serializer()
        refdata_serializer.omit_related = True
        serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = LicenseModelSerializer(required=False, many=True)
    access_type = AccessType.get_serializer_field(required=False)
    description = serializers.JSONField(required=False)

    class Meta:
        model = AccessRights
        fields = ("id", "description", "license", "access_type")

    def create(self, validated_data):
        license_serializer: LicenseModelSerializer = self.fields["license"]

        license_data = validated_data.pop("license", [])
        licenses = license_serializer.create(license_data)

        access_rights = AccessRights.objects.create(**validated_data)
        access_rights.license.set(licenses)

        return access_rights

    def update(self, instance, validated_data):
        license_serializer: LicenseModelSerializer = self.fields["license"]

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
        if validated_data.get("dataset_id") is None:
            validated_data["dataset_id"] = self.context.get("dataset_pk")
        if validated_data.get("dataset_id") is None:
            raise serializers.ValidationError(detail="dataset_id is required for DatasetActor")
        return DatasetActor.objects.create(**validated_data, actor=actor)

    def update(self, instance, validated_data):
        if actor_data := validated_data.pop("actor", None):
            self.fields["actor"].update(instance.actor, actor_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if org := rep["actor"].get("organization"):
            rep["actor"]["organization"] = {
                "id": org.get("id"),
                "pref_label": org.get("pref_label"),
                "url": org.get("url"),
                "code": org.get("code"),
                "in_scheme": org.get("in_scheme"),
                "homepage": org.get("homepage"),
            }
        return rep

    class Meta:
        model = DatasetActor
        fields = ("id", "role", "actor")
        list_serializer_class = CommonListSerializer


class MetadataProviderModelSerializer(AbstractDatasetModelSerializer):
    user = MetaxUserModelSerializer()

    class Meta:
        model = MetadataProvider
        fields = ("id", "user", "organization")

    def create(self, validated_data):
        user = None

        if user_data := validated_data.pop("user", None):
            user, created = get_user_model().objects.get_or_create(**user_data)

        new_metadata_provider: MetadataProvider = MetadataProvider.objects.create(
            user=user, **validated_data
        )

        return new_metadata_provider

    def update(self, instance, validated_data):
        user_serializer = self.fields["user"]
        user_instance = instance.user

        if user_data := validated_data.pop("user", None):
            instance.user = update_or_create_instance(user_serializer, user_instance, user_data)

        return super().update(instance, validated_data)


class OtherIdentifierListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        # Map the other_identifiers instance objects by their notation value
        notation_mapping = {
            other_id.notation: other_id for other_id in instance.other_identifiers.all()
        }
        data_mapping = {item["notation"]: item for item in validated_data}
        ret = []

        # Perform creations and updates
        for notation, data in data_mapping.items():
            other_identifiers = notation_mapping.get(notation, None)
            if other_identifiers is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(other_identifiers, data))

        # Perform deletions
        for notation, other_id in notation_mapping.items():
            if notation not in data_mapping:
                other_id.delete()

        return ret


class OtherIdentifierModelSerializer(AbstractDatasetModelSerializer):
    identifier_type = IdentifierType.get_serializer()(read_only=False, required=False)

    class Meta:
        model = OtherIdentifier
        fields = ("notation", "identifier_type", "old_notation")
        list_serializer_class = OtherIdentifierListSerializer

    def create(self, validated_data):
        identifier_type = None
        identifier_type_data = validated_data.pop("identifier_type", None)

        if identifier_type_data not in EMPTY_VALUES:
            identifier_type = IdentifierType.objects.get(url=identifier_type_data.get("url"))

        other_identifiers = OtherIdentifier.objects.create(
            identifier_type=identifier_type, **validated_data
        )

        return other_identifiers

    def update(self, instance, validated_data):
        identifier_type = None
        identifier_type_data = validated_data.pop("identifier_type", None)

        if identifier_type_data not in EMPTY_VALUES:
            identifier_type = IdentifierType.objects.get(url=identifier_type_data.get("url"))
        instance.identifier_type = identifier_type

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.identifier_type is None:
            rep.pop("identifier_type", None)

        if instance.old_notation is None:
            rep.pop("old_notation", None)

        return rep
