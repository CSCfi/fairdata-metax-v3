import logging
from typing import Optional

from django.core.exceptions import MultipleObjectsReturned
from django.forms import model_to_dict
from rest_framework import serializers

from apps.actors.models import Person, Organization
from apps.actors.serializers import ActorModelSerializer, PersonModelSerializer
from apps.core.models import DatasetActor, EventOutcome, LifecycleEvent, Provenance, Dataset
from apps.core.serializers import DatasetActorProvenanceSerializer, SpatialModelSerializer

logger = logging.getLogger(__name__)


class ProvenanceModelSerializer(serializers.ModelSerializer):
    spatial = SpatialModelSerializer(many=False, required=False)
    lifecycle_event = LifecycleEvent.get_serializer_field(required=False)
    event_outcome = EventOutcome.get_serializer_field(required=False)
    is_associated_with = DatasetActorProvenanceSerializer(many=True, required=False)

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
            ActorModelSerializer(x).data for x in instance.is_associated_with.all()
        ]
        return representation

    def create(self, validated_data):
        """creates a single Provenance record within the database"""

        # Define local variables
        spatial_serializer: SpatialModelSerializer = self.fields["spatial"]
        spatial_data = validated_data.pop("spatial", None)
        is_associated_with_data = validated_data.pop("is_associated_with", None)
        spatial = None
        is_associated_with = []
        dataset = Dataset.available_objects.get(id=validated_data["dataset_id"])

        # Check if spatial data exists
        if spatial_data:
            spatial = spatial_serializer.create(spatial_data)

        # Check if is_associated_with data exists
        if is_associated_with_data:
            for actor_data in is_associated_with_data:
                # It is desired to have different actor objects, even if there are duplicates.
                # Linking could cause effects on unrelated datasets.

                person: Optional[Person] = None
                org: Optional[Organization] = None

                if "person" in actor_data:
                    person_data = actor_data["person"]
                    person_name = person_data["name"]
                    email = person_data.get("email")
                    external_id = person_data.get("external_id")
                    person, created = Person.available_objects.get_or_create(
                        name=person_name,
                        email=email,
                        external_id=external_id,
                        part_of_actor__datasetactor__dataset_id=dataset.id,
                    )
                    logger.info(f"{person=}, {created=}")

                if "organization" in actor_data:
                    org_data = actor_data["organization"]
                    pref_label = org_data["pref_label"]
                    code = org_data.get("code")
                    in_scheme = org_data.get("in_scheme")
                    url = org_data.get("url")
                    org, created = Organization.available_objects.get_or_create(
                        code=code, in_scheme=in_scheme, pref_label=pref_label, url=url
                    )

                # Need to check if the actor is already in the dataset.
                # Otherwise would duplicate same actor on same roles.
                if DatasetActor.objects.filter(
                    organization=org, person=person, dataset_id=validated_data["dataset_id"]
                ).exists():
                    dataset_actor = DatasetActor.objects.get(
                        organization=org, person=person, dataset_id=validated_data["dataset_id"]
                    )
                else:
                    creation_kwargs = {
                        "person": person,
                        "organization": org,
                        "dataset_id": validated_data["dataset_id"],
                    }
                    if person.part_of_actor is not None:
                        creation_kwargs["actor_ptr"] = person.part_of_actor
                    dataset_actor = DatasetActor(**creation_kwargs)

                if dataset_actor:
                    dataset_actor.add_role(dataset_actor.RoleChoices.PROVENANCE)
                    dataset_actor.save()
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
            logger.debug(f"{is_associated_with_actors=}")
            instance.is_associated_with.set([x.id for x in is_associated_with_actors])

        return super().update(instance, validated_data)
