# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from typing import List, Optional

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.settings import api_settings
from watson.search import skip_index_update

from apps.cache.serializer_cache import SerializerCacheSerializer
from apps.common.serializers import (
    CommonListSerializer,
    CommonModelSerializer,
    CommonNestedModelSerializer,
    OneOf,
)
from apps.common.serializers.fields import (
    ConstantField,
    ListValidChoicesField,
    NoopField,
    handle_private_emails,
)
from apps.core.models.access_rights import AccessTypeChoices
from apps.core.helpers import clean_pid
from apps.core.models import DataCatalog, Dataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.models.data_catalog import GeneratedPIDType
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
from apps.core.serializers.dataset_metrics_serializer import DatasetMetricsSerializer
from apps.core.serializers.metadata_provider_serializer import MetadataProviderModelSerializer
from apps.core.serializers.preservation_serializers import PreservationModelSerializer
from apps.core.serializers.project_serializer import ProjectModelSerializer

# for preventing circular import, using submodule instead of apps.core.serializers
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

from .dataset_files_serializer import FileSetSerializer

logger = logging.getLogger(__name__)


class VersionSerializer(CommonModelSerializer):
    version = serializers.IntegerField(source="version_number", read_only=True)

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

    def get_version(self, instance):
        return instance.version_number

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


class DatasetListSerializer(CommonListSerializer):

    def collect_pids(self, data: List[Dataset]):
        """Collect persistent identifiers used in dataset relations."""
        pids = set()
        for dataset in data:
            # Relations and other_identifiers should be prefetched
            for relation in dataset.relation.all():
                if pid := relation.entity.entity_identifier:
                    pids.add(clean_pid(pid))
            for oi in dataset.other_identifiers.all():
                if pid := oi.notation:
                    pids.add(clean_pid(pid))
        return pids

    def map_pids_to_datasets(self, data):
        """Save mapping of persistent_identifier to dataset id to serializer context."""
        pids = self.collect_pids(data)
        pids_ids = Dataset.available_objects.filter(
            persistent_identifier__in=pids, state=Dataset.StateChoices.PUBLISHED
        ).values_list("persistent_identifier", "id")
        mapping = {}
        for pid, id in pids_ids:
            mapping.setdefault(pid, []).append(id)
        self.context["datasets_by_pid"] = mapping

    def to_representation(self, data):
        self.map_pids_to_datasets(data)
        return super().to_representation(data)


class DatasetSerializer(CommonNestedModelSerializer, SerializerCacheSerializer):
    metadata_repository = ConstantField(value="Fairdata")
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
    spatial = SpatialModelSerializer(required=False, many=True, lazy=True)
    temporal = TemporalModelSerializer(required=False, many=True, lazy=True)
    relation = EntityRelationSerializer(required=False, many=True)
    preservation = PreservationModelSerializer(required=False, many=False)
    provenance = ProvenanceModelSerializer(required=False, many=True, lazy=True)
    projects = ProjectModelSerializer(required=False, many=True)
    dataset_versions = serializers.SerializerMethodField()
    allowed_actions = DatasetAllowedActionsSerializer(read_only=True, source="*")
    created = serializers.DateTimeField(required=False, read_only=False)
    modified = serializers.DateTimeField(required=False, read_only=False)
    next_draft = LinkedDraftSerializer(read_only=True)
    draft_of = LinkedDraftSerializer(read_only=True)
    version = serializers.IntegerField(source="version_number", read_only=True)
    metrics = DatasetMetricsSerializer(read_only=True)  # Included when include_metrics=true
    pid_type = NoopField(help_text="No longer in use. Replaced by generate_pid_on_publish.")
    generate_pid_on_publish = ListValidChoicesField(
        choices=GeneratedPIDType.choices, required=False, allow_null=True
    )
    pid_generated_by_fairdata = serializers.BooleanField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.versions_serializer = VersionSerializer(
            many=True
        )  # Avoid initing VersionSerializer multiple times

    def can_view_drafts(self, instance) -> bool:
        """Return true if user can see drafts related to an instance they can see."""
        return (
            instance.state == Dataset.StateChoices.DRAFT
            or instance.has_permission_to_see_drafts(self.context["request"].user)
        )

    def get_version(self, instance):
        return instance.version_number

    def get_dataset_versions(self, instance):
        if version_set := instance.dataset_versions:
            # Use prefetched results stored in _datasets when available
            versions = getattr(version_set, "_datasets", None) or version_set.datasets(
                manager="all_objects"
            ).order_by("-created").prefetch_related(*Dataset.dataset_versions_prefetch_fields)

            has_drafts = any(
                dataset for dataset in versions if dataset.state != Dataset.StateChoices.PUBLISHED
            )
            if has_drafts and not self.can_view_drafts(instance):
                versions = [
                    dataset
                    for dataset in versions
                    if dataset.state == Dataset.StateChoices.PUBLISHED
                ]

            self.versions_serializer._context = self.context
            return self.versions_serializer.to_representation(versions)

    # Fields that should be left unchanged when omitted from PUT
    no_put_default_fields = {
        "id",
        "state",
        "metadata_owner",
        "cumulative_state",
    }

    def get_fields(self):
        fields = super().get_fields()
        if not self.context["view"].query_params.get("include_allowed_actions"):
            fields.pop("allowed_actions", None)
        if not self.context["view"].query_params.get("include_metrics"):
            fields.pop("metrics", None)
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

    def omit_pid_fields(self, instance: Dataset, ret: dict):
        if instance.persistent_identifier:
            ret.pop("generate_pid_on_publish", None)
        else:
            ret.pop("pid_generated_by_fairdata", None)

    def handle_owner_user(self, instance: Dataset, ret: dict):
        """Show dataset owner user if request user has editing permission."""
        has_edit_permission = instance.has_permission_to_edit(self.context["request"].user)
        metadata_owner = ret.get("metadata_owner")
        if metadata_owner and "user" in metadata_owner:
            if has_edit_permission:
                metadata_owner["user"] = metadata_owner["user"].value
            else:
                metadata_owner.pop("user")

    def handle_access_rights_private_fields(self, instance: Dataset, ret: dict):
        access_rights = ret.get("access_rights")
        if not access_rights:
            return

        field = "data_access_reviewer_instructions"
        if access_rights.get(field):
            has_edit_permission = instance.has_permission_to_edit(self.context["request"].user)
            if has_edit_permission:
                access_rights[field] = access_rights[field].value
            else:
                access_rights.pop(field)

    def to_representation(self, instance: Dataset):
        instance.ensure_prefetch()
        request = self.context["request"]
        ret = super().to_representation(instance)

        # Drafts should be hidden from users without access to them
        if not self.can_view_drafts(instance):
            ret.pop("draft_revision", None)
            ret.pop("next_draft", None)
            ret.pop("draft_of", None)

        has_emails = self.context.pop("has_emails", False)

        # Save to serializer cache
        if cache := self.cache:
            if value_context := cache.get_value_context(instance):
                has_emails = has_emails or value_context.get("has_emails", False)
            cache.set_value(
                instance, ret, value_context={"has_emails": has_emails}, only_if_modified=True
            )

        view = self.context["view"]
        if view.query_params.get("expand_catalog"):
            ret["data_catalog"] = DataCatalogModelSerializer(
                instance.data_catalog, context={"request": request}
            ).data

        if fields := view.query_params.get("fields"):
            not_found = [field for field in fields if field not in self.fields]
            if len(not_found):
                raise serializers.ValidationError(
                    {"fields": f"Fields not found in dataset: {','.join(not_found)}"}
                )
            ret = {k: v for k, v in ret.items() if k in fields}

        self.omit_pid_fields(instance, ret)
        self.handle_owner_user(instance, ret)
        self.handle_access_rights_private_fields(instance, ret)

        if has_emails:
            # Handle email values. Copies dicts and lists to avoid accidentally modifying
            # data that has not yet been committed to cache.
            handle_private_emails(
                ret,
                show_emails=instance.has_permission_to_edit(request.user),
                ignore_fields={  # These fields should not contain PrivateEmailValue objects
                    "access_rights",
                    "api_version",
                    "created",
                    "cumulative_state",
                    "data_catalog",
                    "infrastructure",
                    "dataset_versions",
                    "description",
                    "field_of_science",
                    "fileset",
                    "id",
                    "issued",
                    "keyword",
                    "language",
                    "metadata_owner",
                    "metadata_repository",
                    "modified",
                    "other_identifiers",
                    "persistent_identifier",
                    "published_revision",
                    "relation",
                    "remote_resources",
                    "spatial",
                    "state",
                    "temporal",
                    "theme",
                    "title",
                    "version",
                },
            )
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
            "metadata_repository",
            "metrics",
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
            "generate_pid_on_publish",
            "infrastructure",
            "issued",
            "keyword",
            "language",
            "metadata_owner",
            "other_identifiers",
            "persistent_identifier",
            "pid_generated_by_fairdata",  # read only
            "pid_type",  # deprecated
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
        list_serializer_class = DatasetListSerializer

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

    def _validate_data(self, data, errors):
        """Check data constraints."""
        existing_fileset = None
        existing_remote_resources = None
        if self.instance:
            existing_fileset = getattr(self.instance, "file_set", None)
            existing_remote_resources = self.instance.remote_resources.all()
        _user = self.context["request"].user
        preservation = data.get("preservation", None)
        if preservation and not (
            _user.is_superuser or any(group.name == "pas" for group in _user.groups.all())
        ):
            errors["preservation"] = "Only PAS users are allowed to set preservation"
        fileset = data.get("file_set", existing_fileset)
        remote_resources = data.get("remote_resources", existing_remote_resources)
        if fileset and remote_resources:
            errors[api_settings.NON_FIELD_ERRORS_KEY] = (
                "Cannot have files and remote resources in the same dataset."
            )
        return errors

    @classmethod
    def validate_new_catalog(
        cls, dataset: Optional[Dataset], new_data_catalog: Optional[DataCatalog] = None
    ):
        old_catalog = None
        if dataset:  # Omit dataset to indicate creating new dataset
            old_catalog = dataset.data_catalog

        if old_catalog and old_catalog != new_data_catalog:
            raise serializers.ValidationError({"data_catalog": "Cannot change data catalog."})

    @classmethod
    def validate_new_pid(
        cls,
        dataset: Optional["Dataset"],
        new_pid: Optional[str] = None,
        new_data_catalog: Optional[DataCatalog] = None,
    ):
        """Validate that user-provided persistent_identifier is allowed for dataset."""
        msg = None
        data_catalog = new_data_catalog
        old_pid = None
        if dataset:  # Omit dataset to indicate creating new dataset
            old_pid = dataset.persistent_identifier
            data_catalog = data_catalog or dataset.data_catalog

        if new_pid == old_pid:
            return  # No change, no need to validate new value

        if data_catalog and not data_catalog.allow_external_pid:
            msg = "Assigning user-defined PID is not supported by the catalog."

        if dataset:
            if dataset.pid_generated_by_fairdata:
                msg = "Changing generated PID is not allowed."
            elif dataset.generate_pid_on_publish:
                msg = "Cannot assign user-defined PID when using generate_pid_on_publish."

        # PIDs starting wih draft: are reserved for "draft_of" draft datasets
        if new_pid and new_pid.startswith("draft:"):
            msg = "Cannot assign draft PID."

        if msg:
            raise serializers.ValidationError({"persistent_identifier": msg})

    def to_internal_value(self, data):
        if self.instance:  # dataset actors need dataset in context
            self.context["dataset"] = self.instance
        else:
            self.context["dataset"] = None
        _data = super().to_internal_value(data)

        errors = {}
        errors = self._validate_timestamps(_data, errors)
        errors = self._validate_data(_data, errors)

        if errors:
            raise serializers.ValidationError(errors)

        # Assign API version
        _data["api_version"] = 3
        return _data

    def update(self, instance: Dataset, validated_data):
        instance._updating = True
        validated_data["last_modified_by"] = self.context["request"].user

        if "data_catalog" in validated_data:
            self.validate_new_catalog(
                dataset=instance,
                new_data_catalog=validated_data["data_catalog"],
            )

        if "persistent_identifier" in validated_data:
            self.validate_new_pid(
                dataset=instance,
                new_pid=validated_data["persistent_identifier"],
                new_data_catalog=validated_data.get("data_catalog"),
            )

        # Ensure modification timestamp gets set on PATCH which does not use model defaults
        if "modified" not in validated_data:
            validated_data["modified"] = timezone.now()

        dataset: Dataset = super().update(instance, validated_data=validated_data)
        instance._updating = False

        # Remove old data from prefetched objects cache
        # to ensure stale data is not used in V2 integration.
        if prefetch_cache := getattr(dataset, "_prefetched_objects_cache", None):
            dataset.is_prefetched = False
            prefetch_cache.clear()
        return dataset

    def create(self, validated_data):
        validated_data["last_modified_by"] = self.context["request"].user
        self.validate_new_catalog(
            dataset=None,
            new_data_catalog=validated_data.get("data_catalog"),
        )
        self.validate_new_pid(
            dataset=None,
            new_pid=validated_data.get("persistent_identifier"),
            new_data_catalog=validated_data.get("data_catalog"),
        )

        if validated_data.get("access_rights", False):
            is_ida_catalog = (
                validated_data.get("data_catalog")
                and ("ida" in validated_data.get("data_catalog").storage_services
                or "pas" in validated_data.get("data_catalog").storage_services)
            )
            is_open_access = (
                validated_data["access_rights"]["access_type"].url == AccessTypeChoices.OPEN
            )

            if (
                is_ida_catalog
                and validated_data.get("access_rights", {}).get("show_data_metadata") is None
            ):
                if not is_open_access:
                    validated_data["access_rights"]["show_data_metadata"] = False
                else:
                    validated_data["access_rights"]["show_data_metadata"] = True

        # Always initialize dataset as draft. This allows assigning
        # reverse and many-to-many relations to the newly created
        # dataset before it is actually published.
        state = validated_data.pop("state", None)
        instance: Dataset
        if state == Dataset.StateChoices.PUBLISHED:
            with skip_index_update():  # Don't add draft to search index if publish fails
                instance = super().create(validated_data=validated_data)
            # Now reverse and many-to-many relations have been assigned, try to publish
            instance.publish()
        else:
            instance = super().create(validated_data=validated_data)
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
