import logging
from typing import Dict

from rest_framework import serializers

from apps.common.helpers import deduplicate_list, has_values
from apps.common.serializers import CommonListSerializer
from apps.common.serializers.validators import AnyOf
from apps.core.models import DatasetActor
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.serializers.dataset_actor_serializers.member_serializer import (
    DatasetMemberContext,
    DatasetMemberSerializer,
    UUIDOrTagField,
)
from apps.core.serializers.dataset_actor_serializers.organization_serializer import (
    DatasetOrganizationSerializer,
)
from apps.core.serializers.dataset_actor_serializers.person_serializer import (
    DatasetPersonSerializer,
)

logger = logging.getLogger(__name__)


class DatasetActorSerializer(DatasetMemberSerializer):
    """Serializer for dataset actor.

    Same actor can be multiple times in the same dataset.

    As a special case, allows roles for same actor to be specified in multiple objects.
    E.g. `{"id": x, "roles": ["creator"]}` and `{"id": x, "roles": ["publisher"]}`
    in the same request will produce `{"id": x, "roles": ["creator", "publisher]}`.
    """

    id = UUIDOrTagField(required=False)

    # Organization is normally required but can be left out when it can be determined with id.
    # Having it as required here means it shows as required in swagger.
    organization = DatasetOrganizationSerializer(required=True, allow_null=False)
    person = DatasetPersonSerializer(required=False, allow_null=True)

    partial_update_fields = {"id", "roles", "actors_order"}  # Fields allowed for partial update

    def validate_save(self, validated_data, instance=None):
        validated_data = super().validate_save(validated_data, instance)
        if not validated_data.get("organization") and not self.context.get("migrating"):
            raise serializers.ValidationError({"organization": "This field is required"})
        AnyOf(["person", "organization"])(validated_data)

    def to_internal_value(self, data) -> Dict:
        # Make organization field optional when updating actor so it can be determined
        # with id instead of being explicitly defined in the request.
        fields = self.fields
        fields.get("organization").required = False
        fields.get("organization").allow_null = True
        return super().to_internal_value(data)

    def get_dataset_actors(self, dataset) -> Dict[str, DatasetMemberContext]:
        actors = {}

        def add_actor(actor):
            if actor:
                actors[str(actor.id)] = DatasetMemberContext(
                    object=actor, is_existing=True, existing_data=self.get_existing_data(actor)
                )

        for actor in dataset.actors.all():
            add_actor(actor)

        for provenance in dataset.provenance.all():
            for actor in provenance.is_associated_with.all():
                add_actor(actor)

        return actors

    def get_dataset_members(self) -> Dict[str, DatasetMemberContext]:
        if "dataset_actors" not in self.context:
            dataset: Dataset = self.context.get("dataset")
            if dataset:
                self.context["dataset_actors"] = self.get_dataset_actors(dataset)
            else:
                self.context["dataset_actors"] = {}
        return self.context["dataset_actors"]

    def get_comparison_data(self, value, depth=0):
        if depth == 0:  # allow multiple actor references have different roles
            value = {**value}
            value.pop("roles", None)
            value.pop("actors_order", None)
            if not has_values(value, exclude=self.partial_update_fields):
                return None
        return super().get_comparison_data(value, depth)

    def update_save_data(self, member: DatasetMemberContext, validated_data: dict):
        """Merge roles from all actor objects with same id."""
        roles = None
        if member.save_data and (
            validated_data.get("roles") is not None or member.save_data.get("roles") is not None
        ):
            # Combine role lists
            old_roles = member.save_data.get("roles") or []
            new_roles = validated_data.get("roles") or []
            roles = deduplicate_list([*old_roles, *new_roles])

        actors_order = validated_data.get("actors_order")
        if (
            actors_order is not None
            and member.save_data
            and member.save_data.get("actors_order") is not None
        ):
            # Use first order position if there are multiple
            actors_order = min(actors_order, member.save_data.get("actors_order"))

        super().update_save_data(member, validated_data)

        if roles is not None:
            member.save_data["roles"] = roles

        if actors_order is not None:
            member.save_data["actors_order"] = actors_order

    class Meta:
        model = DatasetActor
        fields = ("id", "roles", "person", "organization")

        # Make CommonListSerializer assign actors_order field when serializing Dataset.actors
        ordering_fields = {"Dataset.actors": "actors_order"}

        list_serializer_class = CommonListSerializer


class DatasetActorProvenanceSerializer(DatasetActorSerializer):
    class Meta(DatasetActorSerializer.Meta):
        fields = ("id", "person", "organization")  # no roles
