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
from rest_framework.settings import api_settings

from apps.common.serializers import (
    CommonListSerializer,
    CommonModelSerializer,
    CommonNestedModelSerializer,
    OneOf,
)
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
from apps.core.serializers.data_catalog_serializer import DataCatalogModelSerializer
from apps.core.serializers.dataset_actor_serializers import DatasetActorSerializer
from apps.core.serializers.dataset_allowed_actions import DatasetAllowedActionsSerializer
from apps.core.serializers.metadata_provider_serializer import MetadataProviderModelSerializer
from apps.core.serializers.preservation_serializers import PreservationModelSerializer
from apps.core.serializers.project_serializer import ProjectModelSerializer

# for preventing circular import, using submodule instead of apps.core.serializers
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

from .dataset_files_serializer import FileSetSerializer

logger = logging.getLogger(__name__)


class VersionSerializer(CommonModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id",
            "title",
            "persistent_identifier",
            "state",
            "created",
            "removed",
            "deprecated",
            "next_draft",
            "draft_of",
            "version",
        ]
        list_serializer_class = CommonListSerializer

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if not instance.has_permission_to_see_drafts(self.context["request"].user):
            ret.pop("next_draft", None)
            ret.pop("draft_of", None)

        return ret


class LinkedDraftSerializer(CommonNestedModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "persistent_identifier",
            "created",
            "modified",
            "title",
            "cumulative_state",
        )
        read_only_fields = fields


class DatasetSerializer(CommonNestedModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False, allow_null=True, many=False)
    field_of_science = FieldOfScience.get_serializer_field(required=False, many=True)
    infrastructure = ResearchInfra.get_serializer_field(required=False, many=True)
    actors = DatasetActorSerializer(required=False, many=True)
    fileset = FileSetSerializer(required=False, source="file_set", allow_null=True)
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
    projects = ProjectModelSerializer(required=False, many=True)
    dataset_versions = serializers.SerializerMethodField()
    allowed_actions = DatasetAllowedActionsSerializer(read_only=True, source="*")
    created = serializers.DateTimeField(required=False, read_only=False)
    modified = serializers.DateTimeField(required=False, read_only=False)
    next_draft = LinkedDraftSerializer(read_only=True)
    draft_of = LinkedDraftSerializer(read_only=True)

    def get_dataset_versions(self, instance):
        if version_set := instance.dataset_versions:
            # Use prefetched results stored in _datasets when available
            versions = getattr(version_set, "_datasets", None) or version_set.datasets(
                manager="all_objects"
            ).order_by("-version").prefetch_related("draft_of", "next_draft")

            if not instance.has_permission_to_see_drafts(self.context["request"].user):
                versions = [
                    dataset
                    for dataset in versions
                    if dataset.state == Dataset.StateChoices.PUBLISHED
                ]

            return VersionSerializer(
                instance=versions,
                many=True,
                context=self.context,
            ).data

    # Fields that should be left unchanged when omitted from PUT
    no_put_default_fields = {
        "id",
        "state",
        "metadata_owner",
        "persistent_identifier",
        "cumulative_state",
    }

    def get_fields(self):
        fields = super().get_fields()
        if not self.context["view"].query_params.get("include_allowed_actions"):
            fields.pop("allowed_actions", None)
        return fields

    def save(self, **kwargs):
        if self.instance:
            if (
                "state" in self._validated_data
                and self._validated_data["state"] != self.instance.state
            ):
                raise serializers.ValidationError(
                    {"state": "Value cannot be changed directly for an existing dataset."}
                )

        # If missing, assign metadata owner with metadata_owner.save()
        if not (self.instance and self.instance.metadata_owner):
            # Nested serializer is not called with None,
            # so use {} as "empty" value.
            if not self._validated_data.get("metadata_owner"):
                self._validated_data["metadata_owner"] = {}
        return super().save(**kwargs)

    def to_representation(self, instance: Dataset):
        request = self.context["request"]
        self.context["show_emails"] = instance.has_permission_to_edit(request.user)
        ret = super().to_representation(instance)

        # Drafts should be hidden from users without access to them
        if not instance.has_permission_to_see_drafts(request.user):
            ret.pop("draft_revision", None)
            ret.pop("next_draft", None)
            ret.pop("draft_of", None)

        view = self.context["view"]
        if view.query_params.get("expand_catalog"):
            ret["data_catalog"] = DataCatalogModelSerializer(
                instance.data_catalog, context={"request": request}
            ).data

        return ret

    class Meta:
        model = Dataset
        read_only_fields = (
            "created",
            "cumulation_started",
            "cumulation_ended",
            "deprecated",
            "removed",
            "modified",
            "dataset_versions",
            "published_revision",
            "draft_revision",
            "allowed_actions",
            "draft_of",
            "next_draft",
            "version",
            "api_version",
        )
        fields = (
            "id",  # read only
            "access_rights",
            "actors",
            "bibliographic_citation",
            "cumulative_state",
            "data_catalog",
            "description",
            "field_of_science",
            "fileset",
            "infrastructure",
            "issued",
            "keyword",
            "language",
            "metadata_owner",
            "other_identifiers",
            "persistent_identifier",
            "pid_type",
            "preservation",
            "projects",
            "provenance",
            "relation",
            "remote_resources",
            "spatial",
            "state",
            "temporal",
            "theme",
            "title",
            *read_only_fields,
        )

    def _dc_is_harvested(self, data):
        if self.context["request"].method == "POST":
            if data.get("data_catalog") is not None:
                return DataCatalog.objects.get(id=data["data_catalog"]).harvested
        elif self.context["request"].method in {"PUT", "PATCH"}:
            if self.instance and self.instance.data_catalog:
                return self.instance.data_catalog.harvested
            elif data.get("data_catalog") is not None:
                return DataCatalog.objects.get(id=data["data_catalog"]).harvested
        return None

    def _ds_is_published(self, data):
        state = None
        if data.get("state"):
            state = data["state"]
        elif self.instance:
            state = self.instance.state
        if state == "published":
            return True
        return False

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
        ds_is_published = self._ds_is_published(data)
        if self.context["request"].method in {"POST", "PUT"}:
            if data.get("persistent_identifier") is not None and data.get("data_catalog") is None:
                errors[
                    "persistent_identifier"
                ] = "Can't assign persistent_identifier if data_catalog isn't given"
            elif data.get("data_catalog") is not None:
                if data.get("persistent_identifier") is not None and dc_is_harvested is False:
                    errors[
                        "persistent_identifier"
                    ] = "persistent_identifier can't be assigned to a dataset in a non-harvested data catalog"
                if data.get("persistent_identifier") is None and dc_is_harvested is True:
                    errors[
                        "persistent_identifier"
                    ] = "Dataset in a harvested catalog has to have a persistent identifier"

            if dc_is_harvested is False and ds_is_published and data.get("pid_type") is None:
                errors[
                    "pid_type"
                ] = "If data catalog is not harvested and dataset is published, pid_type needs to be given"

        elif self.context["request"].method in {"PATCH"}:
            if data.get("persistent_identifier") is not None and dc_is_harvested is False:
                errors[
                    "persistent_identifier"
                ] = "persistent_identifier can't be assigned to a dataset in a non-harvested data catalog"

            if (
                self.instance.persistent_identifier is None
                and data.get("persistent_identifier") is None
                and dc_is_harvested is True
            ):
                errors[
                    "persistent_identifier"
                ] = "Dataset in a harvested catalog has to have a persistent identifier"

        return errors

    def _validate_data(self, data, errors):
        """Check data constraints."""
        existing_fileset = None
        existing_remote_resources = None
        if self.instance:
            existing_fileset = getattr(self.instance, "file_set", None)
            existing_remote_resources = self.instance.remote_resources.all()

        fileset = data.get("file_set", existing_fileset)
        remote_resources = data.get("remote_resources", existing_remote_resources)
        if fileset and remote_resources:
            print(fileset, remote_resources)
            errors[
                api_settings.NON_FIELD_ERRORS_KEY
            ] = "Cannot have files and remote resources in the same dataset."
        return errors

    def to_internal_value(self, data):
        if self.instance:  # dataset actors need dataset in context
            self.context["dataset"] = self.instance
        else:
            self.context["dataset"] = None
        _data = super().to_internal_value(data)

        errors = {}
        errors = self._validate_timestamps(_data, errors)
        errors = self._validate_pids(_data, errors)
        errors = self._validate_data(_data, errors)

        if errors:
            raise serializers.ValidationError(errors)

        # Assign API version
        _data["api_version"] = 3
        return _data

    def update(self, instance, validated_data):
        instance._updating = True
        validated_data["last_modified_by"] = self.context["request"].user
        dataset: Dataset = super().update(instance, validated_data=validated_data)
        instance._updating = False
        return dataset

    def create(self, validated_data):
        validated_data["last_modified_by"] = self.context["request"].user

        # Always initialize dataset as draft. This allows assigning
        # reverse and many-to-many relations to the newly created
        # dataset before it is actually published.
        state = validated_data.pop("state", None)
        instance: Dataset = super().create(validated_data=validated_data)

        # Now reverse and many-to-many relations have been assigned, try to publish
        if state == Dataset.StateChoices.PUBLISHED:
            instance.publish()
        return instance


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


class ExpandCatalogQueryParamsSerializer(serializers.Serializer):
    expand_catalog = serializers.BooleanField(
        default=False, help_text=_("Include expanded data catalog in response.")
    )


class LatestVersionQueryParamsSerializer(serializers.Serializer):
    latest_versions = serializers.BooleanField(
        default=False,
        help_text=_("Return only latest datasets versions available for the requesting user."),
    )
