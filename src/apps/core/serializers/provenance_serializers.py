import logging

from apps.common.models import AbstractFreeformConcept
from apps.common.serializers.serializers import CommonListSerializer, CommonNestedModelSerializer
from apps.common.serializers.validators import AnyOf
from apps.core.models import EventOutcome, LifecycleEvent, PreservationEvent, Provenance
from apps.core.models.provenance import ProvenanceVariable, VariableConcept, VariableUniverse
from apps.core.serializers import (
    DatasetActorProvenanceSerializer,
    SpatialModelSerializer,
    TemporalModelSerializer,
)
from apps.core.serializers.common_serializers import EntitySerializer

logger = logging.getLogger(__name__)


class AbstractFreeformConceptSerializer(CommonNestedModelSerializer):
    class Meta:
        fields = ("id", "concept_identifier", "pref_label", "definition", "in_scheme")
        list_serializer_class = CommonListSerializer


class VariableConceptSerializer(AbstractFreeformConceptSerializer):
    class Meta(AbstractFreeformConceptSerializer.Meta):
        model = VariableConcept


class VariableUniverseSerializer(AbstractFreeformConceptSerializer):
    class Meta(AbstractFreeformConceptSerializer.Meta):
        model = VariableUniverse


class ProvenanceVariableSerializer(CommonNestedModelSerializer):
    concept = VariableConceptSerializer(required=False, allow_null=True)
    universe = VariableUniverseSerializer(required=False, allow_null=True)

    class Meta:
        model = ProvenanceVariable
        fields = ("id", "pref_label", "description", "concept", "universe", "representation")
        list_serializer_class = CommonListSerializer


class ProvenanceModelSerializer(CommonNestedModelSerializer):
    spatial = SpatialModelSerializer(required=False, allow_null=True)
    temporal = TemporalModelSerializer(required=False, allow_null=True)
    lifecycle_event = LifecycleEvent.get_serializer_field(required=False, allow_null=True)
    preservation_event = PreservationEvent.get_serializer_field(required=False, allow_null=True)
    event_outcome = EventOutcome.get_serializer_field(required=False, allow_null=True)
    is_associated_with = DatasetActorProvenanceSerializer(many=True, required=False)
    used_entity = EntitySerializer(many=True, required=False)
    variables = ProvenanceVariableSerializer(many=True, required=False)

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
            "variables",
        )
        read_only_fields = ("id",)
        list_serializer_class = CommonListSerializer
        validators = [AnyOf([f for f in fields if f != "id"])]
