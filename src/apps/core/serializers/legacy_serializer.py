import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import CommonNestedModelSerializer
from apps.core.models import LegacyDataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    EntityRelationSerializer,
    OtherIdentifierModelSerializer,
    RemoteResourceSerializer,
    TemporalModelSerializer,
)
from apps.core.serializers.concept_serializers import SpatialModelSerializer
from apps.core.serializers.dataset_actor_serializers import DatasetActorSerializer
from apps.core.serializers.dataset_actor_serializers.actor_serializer import DatasetActorSerializer
from apps.core.serializers.dataset_allowed_actions import DatasetAllowedActionsSerializer
from apps.core.serializers.dataset_files_serializer import FileSetSerializer
from apps.core.serializers.dataset_serializer import DatasetSerializer, LinkedDraftSerializer
from apps.core.serializers.preservation_serializers import PreservationModelSerializer
from apps.core.serializers.project_serializer import ProjectModelSerializer
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

logger = logging.getLogger(__name__)


from django.utils.translation import gettext as _

from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.models import LegacyDataset


class LegacyDatasetModelSerializer(CommonModelSerializer):
    def create(self, validated_data):
        identifier = validated_data["dataset_json"]["identifier"]
        if instance := LegacyDataset.objects.filter(id=identifier).first():
            return self.update(instance, validated_data)
        else:
            validated_data["id"] = identifier
            instance: LegacyDataset = super().create(validated_data)
            return instance.update_from_legacy(context=self.context)

    def update(self, instance, validated_data):
        instance: LegacyDataset = super().update(instance, validated_data)
        return instance.update_from_legacy(context=self.context)

    class Meta:
        model = LegacyDataset
        fields = (
            "id",
            "dataset_json",
            "contract_json",
            "files_json",
            "v2_dataset_compatibility_diff",
        )
        read_only_fields = ("id", "v2_dataset_compatibility_diff")


class LegacyDatasetUpdateSerializer(CommonNestedModelSerializer):
    """Serializer for updating migrated dataset fields.

    Behaves mostly like DatasetSerializer but has less validation and allows
    direct modification of some fields that aren't exposed in the usual .
    """

    actors = DatasetActorSerializer(required=False, many=True)
    access_rights = AccessRightsModelSerializer(required=False, allow_null=True, many=False)
    field_of_science = FieldOfScience.get_serializer_field(required=False, many=True)
    infrastructure = ResearchInfra.get_serializer_field(required=False, many=True)
    actors = DatasetActorSerializer(required=False, many=True)
    fileset = FileSetSerializer(required=False, source="file_set", allow_null=True)
    remote_resources = RemoteResourceSerializer(many=True, required=False)
    language = Language.get_serializer_field(required=False, many=True)
    other_identifiers = OtherIdentifierModelSerializer(required=False, many=True)
    theme = Theme.get_serializer_field(required=False, many=True)
    spatial = SpatialModelSerializer(required=False, many=True)
    temporal = TemporalModelSerializer(required=False, many=True)
    relation = EntityRelationSerializer(required=False, many=True)
    preservation = PreservationModelSerializer(required=False, many=False)
    provenance = ProvenanceModelSerializer(required=False, many=True)
    projects = ProjectModelSerializer(required=False, many=True)
    allowed_actions = DatasetAllowedActionsSerializer(read_only=True, source="*")
    created = serializers.DateTimeField(required=False, read_only=False)
    modified = serializers.DateTimeField(required=False, read_only=False)
    next_draft = LinkedDraftSerializer(read_only=True)
    draft_of = LinkedDraftSerializer(read_only=True)

    class Meta:
        model = LegacyDataset
        nonpublic_fields = [  # Additional fields that are not in the normal public serializer
            "last_cumulative_addition",
            "last_modified_by",
            "cumulation_started",
            "cumulation_ended",
        ]
        fields = [
            field
            for field in DatasetSerializer.Meta.fields
            if field
            not in [
                "metadata_owner",  # assigned directly in LegacyDataset
                "dataset_versions",  # field is not writable
            ]
        ] + nonpublic_fields

    def create(self, validated_data):
        raise NotImplementedError(
            "Creating a new LegacyDataset using the serializer is not supported."
        )

    def update(self, instance, validated_data):
        instance._updating = True
        super().update(instance, validated_data)
        instance._updating = False
        return instance
