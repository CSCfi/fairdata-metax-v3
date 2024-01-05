# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty

from apps.common.serializers import CommonNestedModelSerializer, OneOf
from apps.core.models import DataCatalog, Dataset
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
    actors = DatasetActorSerializer(required=False, many=True)
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
    created = serializers.DateTimeField(required=False, read_only=False)
    modified = serializers.DateTimeField(required=False, read_only=False)

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
            "pid_type",
            "preservation",
            "provenance",
            "relation",
            "remote_resources",
            "spatial",
            "state",
            "temporal",
            # read only
            "created",
            "cumulation_started",
            "first_version",
            "deprecated",
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
            "cumulation_started",
            "first",
            "id",
            "deprecated",
            "last",
            "previous",
            "removed",
            "replaces",
            "other_versions",
        )

    def _dc_is_harvested(self, data):
        if self.context["request"].method == "POST":
            if data.get("data_catalog") != None:
                return DataCatalog.objects.get(id=data["data_catalog"]).harvested
        elif self.context["request"].method in {"PUT", "PATCH"}:
            return DataCatalog.objects.get(id=self.instance.data_catalog).harvested
        return None

    def _validate_timestamps(self, data, errors):
        _now = timezone.now()

        if "modified" in data and data["modified"] > _now:
            errors["modified"] = "Timestamp cannot be in the future"
        if "created" in data and data["created"] > _now:
            errors["created"] = "Timestamp cannot be in the future"

        if self.context["request"].method == "POST":
            if data["modified"] < data["created"]:
                errors["timestamps"] = "Date modified earlier than date created"

        elif self.context["request"].method in {"PUT", "PATCH"}:
            data["created"] = self.instance.created
            if "modified" in data and data["modified"] < data["created"].replace(microsecond=0):
                errors["timestamps"] = "Date modified earlier than date created"
        return errors

    def _validate_pids(self, data, errors):
        dc_is_harvested = self._dc_is_harvested(data)
        if self.context["request"].method == "POST":
            if data.get("persistent_identifier") != None and data.get("data_catalog") == None:
                errors["persistent_identifier"] = serializers.ValidationError(
                    detail="Can't assign persistent_identifier if data_catalog isn't given"
                )
            elif data.get("data_catalog") != None:
                if data.get("persistent_identifier") != None and dc_is_harvested == False:
                    errors["persistent_identifier"] = serializers.ValidationError(
                        detail="persistent_identifier can't be assigned to a dataset in a non-harvested data catalog"
                    )
                if data.get("persistent_identifier") == None and dc_is_harvested == True:
                    errors["persistent_identifier"] = serializers.ValidationError(
                        detail="Dataset in a harvested catalog has to have a persistent identifier"
                    )

        elif self.context["request"].method in {"PUT", "PATCH"}:
            if data.get("persistent_identifier") != None and dc_is_harvested == False:
                errors["persistent_identifier"] = serializers.ValidationError(
                    detail="persistent_identifier can't be assigned to a dataset in a non-harvested data catalog"
                )
            if (
                self.instance.persistent_identifier == None
                and data.get("persistent_identifier") == None
                and dc_is_harvested == True
            ):
                errors["persistent_identifier"] = serializers.ValidationError(
                    detail="Dataset in a harvested catalog has to have a persistent identifier"
                )

        return errors

    def _validate_catalog(self, data, errors):
        if self.context["request"].method == "POST":
            if data.get("data_catalog") == None and data.get("state") == "published":
                errors["data_catalog"] = serializers.ValidationError(
                    detail="Dataset has to have a data catalog when publishing"
                )
        return errors

    def to_internal_value(self, data):
        if self.instance:  # dataset actors need dataset in context
            self.context["dataset"] = self.instance
        _data = super().to_internal_value(data)

        errors = {}
        errors = self._validate_catalog(_data, errors)
        errors = self._validate_timestamps(_data, errors)
        errors = self._validate_pids(_data, errors)

        if errors:
            raise serializers.ValidationError(errors)

        return _data

    def update(self, instance, validated_data):
        validated_data["last_modified_by"] = self.context["request"].user
        dataset = super().update(instance, validated_data=validated_data)
        dataset.create_persistent_identifier()
        return dataset

    def create(self, validated_data):
        validated_data["last_modified_by"] = self.context["request"].user
        dataset = super().create(validated_data=validated_data)
        dataset.create_persistent_identifier()
        return dataset


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
