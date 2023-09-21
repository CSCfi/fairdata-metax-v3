# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import json
import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.actors.models import Organization, Person
from apps.actors.serializers import OrganizationSerializer, PersonModelSerializer
from apps.common.helpers import update_or_create_instance
from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
    AnyOf,
    CommonListSerializer,
    NestedModelSerializer,
)
from apps.core.models import (
    AccessRights,
    CatalogHomePage,
    DatasetActor,
    DatasetPublisher,
    MetadataProvider,
    OtherIdentifier,
)
from apps.core.models.catalog_record import Temporal
from apps.core.models.concepts import AccessType, DatasetLicense, IdentifierType, License
from apps.users.serializers import MetaxUserModelSerializer

logger = logging.getLogger(__name__)


class CatalogHomePageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = CatalogHomePage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields
        list_serializer_class = CommonListSerializer


class DatasetPublisherModelSerializer(NestedModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("id", "name", "homepage")


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
        list_serializer_class = CommonListSerializer

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


class AccessRightsModelSerializer(NestedModelSerializer):
    license = LicenseModelSerializer(required=False, many=True)
    access_type = AccessType.get_serializer_field(required=False, allow_null=True)

    class Meta:
        model = AccessRights
        fields = ("id", "description", "license", "access_type")


class DatasetActorModelSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(many=False, required=False, allow_null=True)
    person = PersonModelSerializer(many=False, required=False, allow_null=True)

    def create(self, validated_data):
        # Object extraction from payload
        org_data = validated_data.pop("organization", None)
        person_data = validated_data.pop("person", None)

        # Final foreign key model objects
        org: Optional[Organization] = None
        person: Optional[Person] = None

        # Organizations are global, persons are local to dataset
        if org_data:
            org, created = Organization.available_objects.get_or_create(**org_data)
        if person_data:
            person = self.fields["person"].create(person_data)

        # dataset id context binding
        if dataset := validated_data.get("dataset"):
            validated_data["dataset_id"] = dataset.id
        if validated_data.get("dataset_id") is None:
            validated_data["dataset_id"] = self.context.get("dataset_pk")
        if validated_data.get("dataset_id") is None:
            raise serializers.ValidationError(detail="dataset_id is required for DatasetActor")
        return DatasetActor.objects.create(organization=org, person=person, **validated_data)

    def update(self, instance, validated_data):
        org_data = validated_data.pop("organization", None)
        person_data = validated_data.pop("person", None)

        if org_data:
            instance.organization = update_or_create_instance(
                self.fields["organization"], instance.organization, org_data
            )
        if person_data:
            instance.person = update_or_create_instance(
                self.fields["person"], instance.person, person_data
            )

        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if org := rep.get("organization"):
            rep["organization"] = {
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
        fields = ("id", "roles", "person", "organization")
        list_serializer_class = CommonListSerializer


class DatasetActorProvenanceSerializer(DatasetActorModelSerializer):
    class Meta(DatasetActorModelSerializer.Meta):
        fields = ("id", "person", "organization")


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
    def update(self, instance: list, validated_data):
        # Map the other_identifiers instance objects by their notation value
        notation_mapping = {other_id.notation: other_id for other_id in instance}
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
    identifier_type = IdentifierType.get_serializer_field(required=False, allow_null=True)

    class Meta:
        model = OtherIdentifier
        fields = ("notation", "identifier_type", "old_notation")
        list_serializer_class = OtherIdentifierListSerializer

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.identifier_type is None:
            rep.pop("identifier_type", None)

        if instance.old_notation is None:
            rep.pop("old_notation", None)

        return rep


class TemporalModelSerializer(AbstractDatasetModelSerializer):
    class Meta:
        model = Temporal
        fields = ("start_date", "end_date")
        list_serializer_class = CommonListSerializer
        validators = [AnyOf(["start_date", "end_date"])]

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] > attrs["end_date"]:
                raise serializers.ValidationError(
                    {
                        "end_date": _(
                            "Value for end_date='{end_date}' is before start_date='{start_date}'."
                        ).format(**attrs)
                    }
                )
        return super().validate(attrs)
