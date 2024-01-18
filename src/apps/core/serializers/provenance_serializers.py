import logging

from apps.common.serializers.serializers import CommonListSerializer, CommonNestedModelSerializer
from apps.core.models import EventOutcome, LifecycleEvent, Provenance, PreservationEvent
from apps.core.serializers import (
    DatasetActorProvenanceSerializer,
    SpatialModelSerializer,
    TemporalModelSerializer,
)
from apps.core.serializers.common_serializers import EntitySerializer

logger = logging.getLogger(__name__)


class ProvenanceModelSerializer(CommonNestedModelSerializer):
    spatial = SpatialModelSerializer(required=False, allow_null=True)
    temporal = TemporalModelSerializer(required=False, allow_null=True)
    lifecycle_event = LifecycleEvent.get_serializer_field(required=False, allow_null=True)
    preservation_event = PreservationEvent.get_serializer_field(required=False, allow_null=True)
    event_outcome = EventOutcome.get_serializer_field(required=False, allow_null=True)
    is_associated_with = DatasetActorProvenanceSerializer(many=True, required=False)
    used_entity = EntitySerializer(many=True, required=False)

    class Meta:
        model = Provenance
        fields = (
            "id",
            "title",
            "description",
            "spatial",
            "temporal",
            "lifecycle_event",
            "preservation_event",
            "event_outcome",
            "outcome_description",
            "is_associated_with",
            "used_entity",
        )
        read_only_fields = ("id",)
        list_serializer_class = CommonListSerializer
