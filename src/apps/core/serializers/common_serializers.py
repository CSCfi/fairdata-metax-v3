# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import (
    AbstractDatasetModelSerializer,
    AbstractDatasetPropertyModelSerializer,
    AnyOf,
    CommonListSerializer,
    CommonNestedModelSerializer,
)
from apps.common.serializers.fields import ChecksumField, MediaTypeField
from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.helpers import get_metax_identifiers_by_pid
from apps.core.models import AccessRights, CatalogHomePage, DatasetPublisher, OtherIdentifier
from apps.core.models.catalog_record import EntityRelation, RemoteResource, Temporal
from apps.core.models.concepts import (
    AccessType,
    DatasetLicense,
    FileType,
    IdentifierType,
    License,
    RelationType,
    ResourceType,
    RestrictionGrounds,
    UseCategory,
)
from apps.core.models.entity import Entity

logger = logging.getLogger(__name__)


class CatalogHomePageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = CatalogHomePage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields
        list_serializer_class = CommonListSerializer


class DatasetPublisherModelSerializer(CommonNestedModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("id", "name", "homepage")


class LicenseModelSerializer(CommonModelSerializer):
    """Custom serializer for License that does not require pref_label

    Conforms use case where AccessRights object can be created with only url-field in license

    """

    description = serializers.JSONField(required=False, allow_null=True)
    url = serializers.URLField(required=False, allow_null=True)
    pref_label = serializers.HStoreField(read_only=True)
    in_scheme = serializers.URLField(max_length=255, read_only=True)

    class Meta:
        model = DatasetLicense
        fields = [
            "custom_url",
            "description",
            "url",
            "pref_label",
            "in_scheme",
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
        refdata_serializer = License.get_serializer_class()
        refdata_serializer.omit_related = True
        serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}


class AccessRightsModelSerializer(CommonNestedModelSerializer):
    license = LicenseModelSerializer(required=False, many=True)
    access_type = AccessType.get_serializer_field(required=True)
    restriction_grounds = RestrictionGrounds.get_serializer_field(required=False, many=True)

    class Meta:
        model = AccessRights
        fields = (
            "id",
            "description",
            "license",
            "access_type",
            "restriction_grounds",
            "available",
        )


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
    metax_ids = serializers.SerializerMethodField()

    class Meta:
        model = OtherIdentifier
        fields = ("notation", "identifier_type", "old_notation", "metax_ids")
        list_serializer_class = OtherIdentifierListSerializer

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        if instance.identifier_type is None:
            rep.pop("identifier_type", None)

        if instance.old_notation is None:
            rep.pop("old_notation", None)

        return rep

    def get_metax_ids(self, instance):
        return get_metax_identifiers_by_pid(instance.notation)


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


class RemoteResourceSerializer(CommonModelSerializer):
    use_category = UseCategory.get_serializer_field()
    file_type = FileType.get_serializer_field(required=False, allow_null=True)
    checksum = ChecksumField(required=False, allow_null=True)
    mediatype = MediaTypeField(required=False, allow_null=True)

    class Meta:
        model = RemoteResource
        fields = [
            "title",
            "description",
            "use_category",
            "access_url",
            "download_url",
            "checksum",
            "file_type",
            "mediatype",
        ]
        list_serializer_class = CommonListSerializer


class EntitySerializer(CommonModelSerializer):
    type = ResourceType.get_serializer_field(required=False, allow_null=True)

    class Meta:
        model = Entity
        fields = [
            "title",
            "description",
            "entity_identifier",
            "type",
        ]
        validators = [AnyOf(["title", "entity_identifier"])]
        list_serializer_class = CommonListSerializer


class EntityRelationSerializer(CommonNestedModelSerializer):
    entity = EntitySerializer()
    relation_type = RelationType.get_serializer_field()
    metax_ids = serializers.SerializerMethodField()

    class Meta:
        model = EntityRelation
        fields = [
            "entity",
            "relation_type",
            "metax_ids",
        ]
        list_serializer_class = CommonListSerializer

    def get_metax_ids(self, instance):
        return get_metax_identifiers_by_pid(instance.entity.entity_identifier)
