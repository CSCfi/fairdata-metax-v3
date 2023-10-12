import logging
from typing import Optional

from apps.actors.models import Organization, Person
from apps.actors.serializers import ActorModelSerializer
from apps.common.serializers.serializers import CommonListSerializer, CommonNestedModelSerializer
from apps.core.models import Dataset, DatasetActor, EventOutcome, LifecycleEvent, Provenance
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
            "event_outcome",
            "outcome_description",
            "is_associated_with",
            "used_entity",
        )
        read_only_fields = ("id",)
        list_serializer_class = CommonListSerializer

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["is_associated_with"] = [
            ActorModelSerializer(x).data for x in instance.is_associated_with.all()
        ]
        return representation

    def create(self, validated_data):
        """creates a single Provenance record within the database"""

        is_associated_with_data = validated_data.pop("is_associated_with", None)
        is_associated_with = []
        dataset = validated_data.get("dataset") or Dataset.available_objects.get(
            id=validated_data["dataset_id"]
        )

        # Check if is_associated_with data exists
        if is_associated_with_data:
            for actor_data in is_associated_with_data:
                # It is desired to have different actor objects, even if there are duplicates.
                # Linking could cause effects on unrelated datasets.

                person: Optional[Person] = None
                org: Optional[Organization] = None

                if person_data := actor_data.get("person"):
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

                if org_data := actor_data.get("organization"):
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
                    organization=org, person=person, dataset_id=dataset.id
                ).exists():
                    dataset_actor = DatasetActor.objects.get(
                        organization=org, person=person, dataset_id=dataset.id
                    )
                else:
                    creation_kwargs = {
                        "person": person,
                        "organization": org,
                        "dataset_id": dataset.id,
                    }
                    if (
                        person
                        and hasattr(person, "part_of_actor")
                        and person.part_of_actor is not None
                    ):
                        creation_kwargs["actor_ptr"] = person.part_of_actor
                    dataset_actor = DatasetActor(**creation_kwargs)

                if dataset_actor:
                    dataset_actor.add_role(dataset_actor.RoleChoices.PROVENANCE)
                    dataset_actor.save()
                    is_associated_with.append(dataset_actor)

        provenance = super().create(validated_data=validated_data)
        if is_associated_with:
            provenance.is_associated_with.set(is_associated_with)
        return provenance

    def update(self, instance, validated_data):
        is_associated_with_serializer = self.fields["is_associated_with"]
        is_associated_with_data = validated_data.pop("is_associated_with", None)
        if is_associated_with_data:
            is_associated_with_actors = is_associated_with_serializer.update(
                instance.is_associated_with.all(), is_associated_with_data
            )
            instance.is_associated_with.set(is_associated_with_actors)

        return super().update(instance, validated_data)
