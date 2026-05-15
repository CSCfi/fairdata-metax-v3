import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import (
    AnyOf,
    CommonListSerializer,
    CommonNestedModelSerializer,
)
from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.helpers import get_metax_identifiers_by_pid
from apps.core.models.catalog_record import EntityRelation
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.concepts import (
    RelationType,
    ResourceType,
)
from apps.core.models.entity import Entity

logger = logging.getLogger(__name__)


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
        if instance.entity.entity_identifier:
            return get_metax_identifiers_by_pid(instance.entity.entity_identifier, self.context)


class ReferencedBySerializer(CommonModelSerializer):
    """Read-only serializer for dataset references referenced_by."""
    id = serializers.UUIDField(read_only=True)
    persistent_identifier = serializers.CharField(read_only=True)
    title = serializers.DictField(read_only=True)

    class Meta:
        model = Dataset
        fields = ["id", "persistent_identifier", "title"]


class ReferenceSerializer(CommonModelSerializer):
    """Read-only serializer for dataset references."""

    referenced_identifier = serializers.CharField(
        source="entity.entity_identifier", read_only=True
    )
    referenced_by = ReferencedBySerializer(source="dataset", read_only=True)
    relation_type = RelationType.get_serializer_field(read_only=True)

    class Meta:
        model = EntityRelation
        fields = [
            "referenced_identifier",
            "referenced_by",
            "relation_type",
        ]
