import logging

from django.core.exceptions import MultipleObjectsReturned
from django.forms import model_to_dict
from rest_framework import serializers

from apps.actors.models import Person
from apps.actors.serializers import ActorModelSerializer, PersonModelSerializer
from apps.core.models import EventOutcome, Provenance, DatasetActor, LifecycleEvent
from apps.core.serializers import DatasetActorModelSerializer, SpatialModelSerializer

logger = logging.getLogger(__name__)


class ProvenanceModelSerializer(serializers.ModelSerializer):
    spatial = SpatialModelSerializer(many=False, required=False)
    lifecycle_event = LifecycleEvent.get_serializer_field(required=False)
    event_outcome = EventOutcome.get_serializer_field(required=False)
    is_associated_with = ActorModelSerializer(many=True, required=False)

    class Meta:
        model = Provenance
        fields = (
            "id",
            "title",
            "description",
            "spatial",
            "lifecycle_event",
            "event_outcome",
            "outcome_description",
            "is_associated_with",
        )
        read_only_fields = ("id",)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["is_associated_with"] = [
            ActorModelSerializer(x.actor).data for x in instance.is_associated_with.all()
        ]
        return representation

    def create(self, validated_data):
        spatial_serializer: SpatialModelSerializer = self.fields["spatial"]

        spatial_data = validated_data.pop("spatial", None)
        is_associated_with_data = validated_data.pop("is_associated_with", None)

        spatial = None
        is_associated_with = []

        if spatial_data:
            spatial = spatial_serializer.create(spatial_data)

        if is_associated_with_data:
            for asso_data in is_associated_with_data:
                actor_serializer = ActorModelSerializer()
                # It is desired to have different actor objects, even if there are duplicates.
                # Linking could cause effects on unrelated datasets.

                actor = actor_serializer.create(asso_data)

                # Need to check if the actor is already in the dataset.
                # Otherwise would duplicate same actor on same role.
                dataset_actor, created = DatasetActor.available_objects.get_or_create(
                    actor__person__name=actor.person.name,
                    actor__organization__pref_label__values__contains=list(
                        actor.organization.pref_label.values()
                    ),
                    dataset_id=validated_data["dataset_id"],
                    defaults={
                        "actor": actor,
                        "dataset_id": validated_data["dataset_id"],
                        "role": "provenance",
                    },
                )
                is_associated_with.append(dataset_actor)

        provenance = Provenance.available_objects.create(
            spatial=spatial,
            **validated_data,
        )
        if len(is_associated_with) > 0:
            provenance.is_associated_with.set(is_associated_with)
        return provenance

    def update(self, instance, validated_data):
        spatial_serializer: SpatialModelSerializer = self.fields["spatial"]
        is_associated_with_serializer = self.fields["is_associated_with"]

        spatial_data = validated_data.pop("spatial", None)
        is_associated_with_data = validated_data.pop("is_associated_with", None)

        if spatial_data:
            spatial_serializer.update(instance.spatial, spatial_data)

        if is_associated_with_data:
            is_associated_with_actors = is_associated_with_serializer.update(
                instance.is_associated_with.all(), is_associated_with_data
            )
            is_associated_with = []
            for actor in is_associated_with_actors:
                dataset_actor, created = DatasetActor.available_objects.get_or_create(
                    role="provenance", actor=actor, dataset_id=instance.dataset_id
                )
                is_associated_with.append(dataset_actor)
            instance.is_associated_with.set(is_associated_with)

        return super().update(instance, validated_data)
