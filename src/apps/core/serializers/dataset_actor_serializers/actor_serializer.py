import logging
from typing import Dict

from django.utils.translation import gettext_lazy as _

from apps.common.helpers import deduplicate_list, has_values
from apps.common.serializers import CommonListSerializer
from apps.common.serializers.validators import AnyOf
from apps.core.models import DatasetActor
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.serializers.dataset_actor_serializers.member_serializer import (
    DatasetMemberContext,
    DatasetMemberSerializer,
    IntegerOrTagField,
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

    id = IntegerOrTagField(required=False)
    organization = DatasetOrganizationSerializer(required=False, allow_null=True)
    person = DatasetPersonSerializer(required=False, allow_null=True)

    partial_update_fields = {"id", "roles"}  # Fields allowed for partial update
    save_validator = AnyOf(["person", "organization"])

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

        super().update_save_data(member, validated_data)

        if roles is not None:
            member.save_data["roles"] = roles

    class Meta:
        model = DatasetActor
        fields = ("id", "roles", "person", "organization")
        list_serializer_class = CommonListSerializer


class DatasetActorProvenanceSerializer(DatasetActorSerializer):
    class Meta(DatasetActorSerializer.Meta):
        fields = ("id", "person", "organization")  # no roles
