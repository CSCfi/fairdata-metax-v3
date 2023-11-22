# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import CommonNestedModelSerializer, OneOf
from apps.core.models import Dataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    DatasetActorModelSerializer,
    EntityRelationSerializer,
    OtherIdentifierModelSerializer,
    RemoteResourceSerializer,
    TemporalModelSerializer,
)
from apps.core.serializers.concept_serializers import SpatialModelSerializer
from apps.core.serializers.dataset_allowed_actions import DatasetAllowedActionsSerializer
from apps.core.serializers.metadata_provider_serializer import MetadataProviderModelSerializer
from apps.core.serializers.preservation_serializers import PreservationModelSerializer

# for preventing circular import, using submodule instead of apps.core.serializers
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

from .dataset_files_serializer import FileSetSerializer

logger = logging.getLogger(__name__)


class DatasetSerializer(CommonNestedModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False, allow_null=True, many=False)
    field_of_science = FieldOfScience.get_serializer_field(required=False, many=True)
    infrastructure = ResearchInfra.get_serializer_field(required=False, many=True)
    actors = DatasetActorModelSerializer(required=False, many=True)
    fileset = FileSetSerializer(required=False, source="file_set")
    remote_resources = RemoteResourceSerializer(many=True, required=False)
    language = Language.get_serializer_field(required=False, many=True)
    metadata_owner = MetadataProviderModelSerializer(required=False)
    other_identifiers = OtherIdentifierModelSerializer(required=False, many=True)
    theme = Theme.get_serializer_field(required=False, many=True)
    spatial = SpatialModelSerializer(required=False, many=True)
    temporal = TemporalModelSerializer(required=False, many=True)
    relation = EntityRelationSerializer(required=False, many=True)
    preservation = PreservationModelSerializer(required=False, many=False)
    provenance = ProvenanceModelSerializer(required=False, many=True)
    last_version = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="dataset-detail"
    )
    previous_version = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="dataset-detail"
    )
    next_version = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="dataset-detail"
    )
    first_version = serializers.HyperlinkedRelatedField(
        many=False, read_only=True, view_name="dataset-detail"
    )
    other_versions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="dataset-detail"
    )
    allowed_actions = DatasetAllowedActionsSerializer(read_only=True, source="*")

    def get_fields(self):
        fields = super().get_fields()

        if not self.context["view"].query_params.get("include_allowed_actions"):
            fields.pop("allowed_actions", None)
        return fields

    def save(self, **kwargs):
        # If missing, assign metadata owner with metadata_owner.save()
        if not (self.instance and self.instance.metadata_owner):
            # Nested serializer is not called with None,
            # so use {} as "empty" value.
            if not self._validated_data.get("metadata_owner"):
                self._validated_data["metadata_owner"] = {}
        super().save(**kwargs)

    def to_representation(self, instance):
        request = self.context.get("request")
        if request:
            see_drafts = instance.has_permission_to_see_drafts(request.user)
            is_historic = hasattr(instance, "_history")
            if not see_drafts and not is_historic:
                instance = instance.latest_published_revision
        return super().to_representation(instance)

    class Meta:
        model = Dataset
        fields = (
            "id",  # read only
            "access_rights",
            "actors",
            "cumulative_state",
            "data_catalog",
            "description",
            "field_of_science",
            "infrastructure",
            "fileset",
            "issued",
            "keyword",
            "language",
            "metadata_owner",
            "other_identifiers",
            "persistent_identifier",
            "theme",
            "title",
            "preservation",
            "provenance",
            "relation",
            "spatial",
            "temporal",
            "remote_resources",
            "state",
            # read only
            "created",
            "cumulation_started",
            "first_version",
            "is_deprecated",
            "removed",
            "last_version",
            "modified",
            "previous_version",
            "next_version",
            "other_versions",
            "published_revision",
            "allowed_actions",
        )
        read_only_fields = (
            "created",
            "cumulation_started",
            "first",
            "id",
            "is_deprecated",
            "last",
            "modified",
            "previous",
            "removed",
            "replaces",
            "other_versions",
        )


class DatasetRevisionsQueryParamsSerializer(serializers.Serializer):
    latest_published = serializers.BooleanField(
        help_text=("Get latest published revision."), required=False
    )
    published_revision = serializers.IntegerField(
        help_text=("Get specific published revision."),
        required=False,
    )
    all_published_revisions = serializers.BooleanField(
        help_text=("Get all published revision. "),
        required=False,
    )

    class Meta:
        validators = [
            OneOf(
                ["latest_published", "published_revision", "all_published_versions"],
                required=False,
                count_all_falsy=True,
            )
        ]
