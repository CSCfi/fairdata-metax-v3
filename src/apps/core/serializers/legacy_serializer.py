import copy
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from watson.search import skip_index_update

from apps.common.helpers import process_nested
from apps.common.serializers import CommonNestedModelSerializer
from apps.core.models import Dataset, LegacyDataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.models.preservation import Preservation
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
from apps.core.serializers.metadata_provider_serializer import MetadataProviderModelSerializer
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

    def save(self, **kwargs):
        try:
            res = super().save(**kwargs)
        except Exception as e:
            # Log errors here to make migration issues easier to debug
            logger.error(e.__repr__())
            raise
        return res

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # Hide non-public fields from response
        def pre_handler(value, path):
            if isinstance(value, dict):
                for key in value.keys():
                    if key in {
                        "email",
                        "telephone",
                        "phone",
                        "access_granter",
                        "rems_identifier",
                        "editor_permissions",
                    }:
                        value[key] = "<hidden>"
            return value

        # Files list can be huge, just report file count
        if legacy_ids := rep.get("legacy_file_ids"):
            file_count = len(legacy_ids)
            rep["legacy_file_ids"] = f"<{file_count} files>"

        return process_nested(copy.deepcopy(rep), pre_handler)

    class Meta:
        model = LegacyDataset
        fields = (
            "id",
            "dataset_json",
            "contract_json",
            "legacy_file_ids",
            "v2_dataset_compatibility_diff",
            "migration_errors",
        )
        read_only_fields = (
            "id",
            "v2_dataset_compatibility_diff",
            "migration_errors",
            "last_successful_migration",
            "invalid_legacy_values",
            "fixed_legacy_values",
        )


class LegacyPreservationSerializer(PreservationModelSerializer):

    dataset_version = serializers.UUIDField(
        source="dataset_version.dataset", required=False, allow_null=True
    )
    dataset_origin_version = serializers.UUIDField(
        source="dataset_origin_version.dataset", required=False, allow_null=True
    )

    def _handle_preservation_versions(self, instance: Preservation, preservation_versions: dict):
        try:
            if preserved := preservation_versions.get("preserved"):
                other = Preservation.objects.get(dataset=preserved["dataset"])
                instance.dataset_version = other
                instance.save()
            elif origin := preservation_versions.get("origin"):
                other = Preservation.objects.get(dataset=origin["dataset"])
                other.dataset_version = instance
                other.save()
        except Preservation.DoesNotExist:
            pass  # Linked dataset has not been migrated yet, skip assigning dataset_version

    def create(self, validated_data: dict):
        preservation_data = {
            "origin": validated_data.pop("dataset_origin_version", None),
            "preserved": validated_data.pop("dataset_version", None),
        }
        instance: Preservation = super().create(validated_data)
        self._handle_preservation_versions(instance, preservation_data)
        return instance

    def update(self, instance: Preservation, validated_data: dict):
        preservation_data = {
            "origin": validated_data.pop("dataset_origin_version", None),
            "preserved": validated_data.pop("dataset_version", None),
        }
        instance = super().update(instance, validated_data)
        self._handle_preservation_versions(instance, preservation_data)
        return instance

    class Meta(PreservationModelSerializer.Meta):
        fields = [
            *PreservationModelSerializer.Meta.fields,
            "dataset_version",
            "dataset_origin_version",
        ]
        extra_kwargs = {"state_modified": {"read_only": False}}


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
    remote_resources = RemoteResourceSerializer(many=True, required=False)
    language = Language.get_serializer_field(required=False, many=True)
    metadata_owner = MetadataProviderModelSerializer(required=True)
    other_identifiers = OtherIdentifierModelSerializer(required=False, many=True)
    theme = Theme.get_serializer_field(required=False, many=True)
    spatial = SpatialModelSerializer(required=False, many=True)
    temporal = TemporalModelSerializer(required=False, many=True)
    relation = EntityRelationSerializer(required=False, many=True)
    preservation = LegacyPreservationSerializer(required=False, many=False)
    provenance = ProvenanceModelSerializer(required=False, many=True)
    projects = ProjectModelSerializer(required=False, many=True)
    allowed_actions = DatasetAllowedActionsSerializer(read_only=True, source="*")
    created = serializers.DateTimeField(required=False, read_only=False)
    modified = serializers.DateTimeField(required=False, read_only=False)
    removed = serializers.DateTimeField(required=False, read_only=False, allow_null=True)
    next_draft = LinkedDraftSerializer(read_only=True)
    draft_of = LinkedDraftSerializer(read_only=True)
    is_legacy = serializers.HiddenField(default=True)
    api_version = serializers.IntegerField()
    id = serializers.UUIDField()
    permissions_id = serializers.UUIDField(required=False, allow_null=True)

    no_put_default_fields = {
        "permissions_id"
    }  # Keep existing permissions_id if one is not provided

    class Meta:
        model = Dataset
        nonpublic_fields = [  # Additional fields that are not in the normal public serializer
            "last_cumulative_addition",
            "last_modified_by",
            "cumulation_started",
            "cumulation_ended",
            "is_legacy",
            "api_version",
            "permissions_id",
        ]
        fields = [
            field
            for field in DatasetSerializer.Meta.fields
            if field
            not in [
                "pid_type",  # field removed
                "metadata_repository",  # field is not writable
                "dataset_versions",  # field is not writable
                "metrics",  # field is not writable
                "fileset",  # assigned directly in LegacyDataset
                "version",  # field is not writable
            ]
        ] + nonpublic_fields

    def create(self, validated_data):
        validated_data["_saving_legacy"] = True
        state = validated_data.pop("state", None)  # Always initialize dataset as draft
        instance: Dataset
        if state == Dataset.StateChoices.PUBLISHED:
            with skip_index_update():  # Don't add draft to search index if publish fails
                instance = super().create(validated_data=validated_data)
            instance.publish()  # Relations have been assigned, try to publish
        else:
            instance = super().create(validated_data=validated_data)
        return instance

    def update(self, instance, validated_data):
        instance._saving_legacy = True
        instance._updating = True
        super().update(instance, validated_data)
        instance._updating = False
        instance._saving_legacy = False

        if getattr(instance, "_prefetched_objects_cache", None):
            # Make sure prefetched relations are refreshed
            instance._prefetched_objects_cache.clear()
        return instance


class LegacyDatasetConversionValidationSerializer(LegacyDatasetUpdateSerializer):
    """Serializer for validating V2->V3 conversion."""

    # Use non-relational field for data_catalog to ignore missing catalogs
    data_catalog = serializers.CharField(required=False)
    metadata_owner = MetadataProviderModelSerializer(required=False)
    id = serializers.UUIDField(required=False)

    class Meta(LegacyDatasetUpdateSerializer.Meta):
        fields = [
            field for field in LegacyDatasetUpdateSerializer.Meta.fields if field != "api_version"
        ]

    no_save_msg = "Dataset saving not supported."

    def save(self, **kwargs):
        raise NotImplementedError(self.no_save_msg)

    def create(self, validated_data):
        raise NotImplementedError(self.no_save_msg)

    def update(self, instance, validated_data):
        raise NotImplementedError(self.no_save_msg)
