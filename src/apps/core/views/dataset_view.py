# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging

from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet
from django.http import Http404
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from django_filters.fields import CSVWidget
from drf_yasg.openapi import TYPE_STRING, Parameter, Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, response, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.reverse import reverse
from watson import search

from apps.common.filters import MultipleCharFilter
from apps.common.helpers import ensure_dict, omit_empty
from apps.common.serializers.serializers import (
    FlushQueryParamsSerializer,
    IncludeRemovedQueryParamsSerializer,
)
from apps.common.views import CommonModelViewSet
from apps.core.models.catalog_record import Dataset, FileSet
from apps.core.models.data_catalog import DataCatalog
from apps.core.models.legacy_converter import LegacyDatasetConverter
from apps.core.models.preservation import Preservation
from apps.core.permissions import DataCatalogAccessPolicy, DatasetAccessPolicy
from apps.core.renderers import DataciteXMLRenderer, FairdataDataciteXMLRenderer
from apps.core.serializers import DatasetSerializer
from apps.core.serializers.contact_serializer import (
    ContactResponseSerializer,
    ContactRolesSerializer,
    ContactSerializer,
)
from apps.core.serializers.dataset_allowed_actions import (
    DatasetAllowedActionsQueryParamsSerializer,
)
from apps.core.serializers.dataset_serializer import (
    DatasetRevisionsQueryParamsSerializer,
    ExpandCatalogQueryParamsSerializer,
    LatestVersionQueryParamsSerializer,
)
from apps.core.serializers.legacy_serializer import LegacyDatasetUpdateSerializer
from apps.core.views.common_views import DefaultValueOrdering
from apps.files.models import File
from apps.files.serializers import DirectorySerializer
from apps.files.views.directory_view import DirectoryCommonQueryParams, DirectoryViewSet
from apps.files.views.file_view import BaseFileViewSet, FileCommonFilterset

from .dataset_aggregation import aggregate_queryset

logger = logging.getLogger(__name__)


class DatasetFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title__values",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )
    data_catalog__id = filters.CharFilter(
        field_name="data_catalog__id",
        lookup_expr="icontains",
        label="data-catalog identifier",
        help_text="filter with substring from data-catalog identifier",
    )

    data_catalog__title = filters.CharFilter(
        field_name="data_catalog__title__values",
        max_length=512,
        lookup_expr="icontains",
        label="data-catalog title",
    )
    actors__person__name = MultipleCharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="person name",
    )
    actors__role = MultipleCharFilter(
        field_name="actors__roles",
        max_length=512,
        lookup_expr="icontains",
        label="actor role",
        conjoined=True,
        widget=CSVWidget,
    )
    metadata_owner__organization = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner organization",
    )
    metadata_owner__user = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner user",
    )
    persistent_identifier = filters.CharFilter(
        max_length=255,
        lookup_expr="exact",
        label="persistent identifier",
    )
    preservation__contract = filters.CharFilter(
        max_length=512,
        label="preservation contract",
        field_name="preservation__contract",
    )
    preservation__state = filters.MultipleChoiceFilter(
        choices=Preservation.PreservationState.choices,
        label="preservation_state",
        field_name="preservation__state",
    )
    state = filters.ChoiceFilter(
        choices=Dataset.StateChoices.choices,
        label="state",
    )

    access_rights__access_type__pref_label = MultipleCharFilter(
        method="filter_access_type",
        label="access_type",
    )

    actors__organization__pref_label = MultipleCharFilter(
        method="filter_organization",
        label="organization name",
    )

    actors__roles__creator = MultipleCharFilter(method="filter_creator", max_length=255)

    field_of_science__pref_label = MultipleCharFilter(
        method="filter_field_of_science",
        label="field of science",
    )

    keyword = MultipleCharFilter(method="filter_keyword", label="keyword")

    infrastructure__pref_label = MultipleCharFilter(
        method="filter_infrastructure",
        label="infrastructure",
    )

    file_type = MultipleCharFilter(
        method="filter_file_type",
        label="file_type",
    )

    projects__title = MultipleCharFilter(
        method="filter_project",
        label="projects",
    )

    deprecated = filters.BooleanFilter(lookup_expr="isnull", exclude=True)
    ordering = DefaultValueOrdering(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        ),
        default="-modified",
    )

    search = filters.CharFilter(method="search_dataset")

    def search_dataset(self, queryset, name, value):
        if value is None or value == "":
            return queryset
        if self.form.cleaned_data.get("ordering") is None:
            return search.filter(queryset=queryset, search_text=value, ranking=True)
        return search.filter(queryset=queryset, search_text=value, ranking=False)

    def filter_access_type(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="access_rights__access_type__pref_label__values__contains",
        )

    def filter_organization(self, queryset, name, value):
        return self._filter_list(
            queryset, value, filter_param="actors__organization__pref_label__values__contains"
        )

    def filter_keyword(self, queryset, name, value):
        return self._filter_list(queryset, value, filter_param="keyword__contains")

    def filter_creator(self, queryset, name, value):
        result = queryset
        for group in value:
            union = None
            for val in group:
                if union is not None:
                    union = union | queryset.filter(
                        Q(actors__roles__contains=["creator"])
                        & (
                            Q(actors__organization__pref_label__values__contains=[val])
                            | Q(actors__person__name__exact=val)
                        )
                    )
                else:
                    union = queryset.filter(
                        Q(actors__roles__contains=["creator"])
                        & (
                            Q(actors__organization__pref_label__values__contains=[val])
                            | Q(actors__person__name__exact=val)
                        )
                    )
            if union is not None:
                result = result & union
        return result.distinct()

    def filter_field_of_science(self, queryset, name, value):
        return self._filter_list(
            queryset, value, filter_param="field_of_science__pref_label__values__contains"
        )

    def filter_infrastructure(self, queryset, name, value):
        return self._filter_list(
            queryset, value, filter_param="infrastructure__pref_label__values__contains"
        )

    def filter_file_type(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="file_set__file_metadata__file_type__pref_label__values__contains",
        )

    def filter_project(self, queryset, name, value):
        return self._filter_list(queryset, value, filter_param="projects__title__values__contains")

    def _filter_list(self, queryset, value, filter_param):
        result = queryset
        for group in value:
            union = None
            for val in group:
                param = {filter_param: [val]}

                if union is not None:
                    union = union | queryset.filter(**param)
                else:
                    union = queryset.filter(**param)
            if union:
                result = result & union
        return result.distinct()

    has_files = filters.BooleanFilter(
        field_name="file_set__files", lookup_expr="isnull", exclude=True, distinct=True
    )
    csc_projects = filters.BaseInFilter(field_name="file_set__storage__csc_project")
    storage_services = filters.BaseInFilter(field_name="file_set__storage__storage_service")

    only_owned_or_shared = filters.BooleanFilter(method="filter_owned_or_shared")

    def filter_owned_or_shared(self, queryset, name, value):
        """Filter datasets owned by or shared with the authenticated user."""
        if value:
            return DatasetAccessPolicy.scope_queryset_owned_or_shared(self.request, queryset)
        return queryset


@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        responses={
            403: Response(
                "unauthorized",
            )
        }
    ),
)
class DatasetViewSet(CommonModelViewSet):
    query_serializers = [
        {"class": LatestVersionQueryParamsSerializer, "actions": ["list"]},
        {
            "class": ExpandCatalogQueryParamsSerializer,
            "actions": ["list", "retrieve"],
        },
        {
            "class": DatasetRevisionsQueryParamsSerializer,
            "actions": ["revisions"],
        },
        {
            "class": DatasetAllowedActionsQueryParamsSerializer,
            "actions": ["retrieve", "list", "create", "update", "partial_update", "revisions"],
        },
        {
            "class": IncludeRemovedQueryParamsSerializer,
            "actions": ["list", "retrieve", "update", "partial_update"],
        },
        {
            "class": FlushQueryParamsSerializer,
            "actions": ["destroy"],
        },
    ]
    access_policy = DatasetAccessPolicy
    serializer_class = DatasetSerializer

    prefetch_fields = (
        "access_rights__access_type",
        "access_rights__license__reference",
        "access_rights__license",
        "access_rights__restriction_grounds",
        "access_rights",
        "actors__organization__homepage",
        "actors__organization__parent__homepage",
        "actors__organization__parent",
        "actors__organization",
        "actors__person__homepage",
        "actors__person",
        "actors",
        "data_catalog",
        "dataset_versions",
        "draft_of",
        "field_of_science",
        "file_set",
        "infrastructure",
        "language",
        "metadata_owner__user",
        "metadata_owner",
        "next_draft",
        "other_identifiers__identifier_type",
        "other_identifiers",
        "preservation",
        "projects__funding__funder__funder_type",
        "projects__funding__funder__organization__homepage",
        "projects__funding__funder__organization__parent__homepage",
        "projects__funding__funder__organization__parent",
        "projects__funding__funder__organization",
        "projects__funding__funder",
        "projects__funding",
        "projects__participating_organizations__homepage",
        "projects__participating_organizations__parent__homepage",
        "projects",
        "provenance__event_outcome",
        "provenance__is_associated_with__organization__homepage",
        "provenance__is_associated_with__organization__parent__homepage",
        "provenance__is_associated_with__organization__parent",
        "provenance__is_associated_with__organization",
        "provenance__is_associated_with__person__homepage",
        "provenance__is_associated_with__person",
        "provenance__is_associated_with",
        "provenance__lifecycle_event",
        "provenance__spatial__reference",
        "provenance__spatial",
        "provenance__temporal",
        "provenance__used_entity__type",
        "provenance__used_entity",
        "provenance__variables__concept",
        "provenance__variables__universe",
        "provenance__variables",
        "provenance",
        "relation__entity__type",
        "relation__entity",
        "relation__relation_type",
        "relation",
        "remote_resources__file_type",
        "remote_resources__use_category",
        "remote_resources",
        "spatial__provenance",
        "spatial__reference",
        "spatial",
        "temporal",
        "theme",
    )

    queryset = Dataset.available_objects.prefetch_related(*prefetch_fields)
    queryset_include_removed = Dataset.all_objects.prefetch_related(*prefetch_fields)

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.query_params.get("latest_versions"):
            # Return only latest versions available for the current user
            available_datasets = self.get_queryset()
            latest_versions = available_datasets.order_by(
                "dataset_versions_id", "-version"
            ).distinct("dataset_versions_id")
            return queryset.filter(id__in=latest_versions)

        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                name="format",
                in_="query",
                description="Metadata output format.",
                type=TYPE_STRING,
                enum=(
                    JSONRenderer.format,
                    DataciteXMLRenderer.format,
                    FairdataDataciteXMLRenderer.format,
                ),
            )
        ]
    )
    @action(
        detail=True,
        url_path="metadata-download",
        renderer_classes=[JSONRenderer, DataciteXMLRenderer, FairdataDataciteXMLRenderer],
    )
    def metadata_download(self, request, pk=None):
        """Return dataset metadata as a file attachment."""
        try:
            obj = self.get_object()
        except Http404:
            return response.Response("Dataset not found.", status=404, content_type="text/plain")

        serializer = self.serializer_class
        serializer_context = self.get_serializer_context()
        extension = "json"

        data = None
        if request.accepted_renderer.media_type == "application/xml":
            extension = "xml"
            data = obj  # XML renderer takes dataset objects
        else:
            data = serializer(obj, context=serializer_context).data

        return response.Response(
            data,
            headers={"Content-Disposition": f"attachment; filename={pk}-metadata.{extension}"},
        )

    def get_queryset(self):
        include_all_datasets = self.query_params.get("include_removed") or self.query_params.get(
            "flush"
        )
        qs: QuerySet
        if include_all_datasets:
            qs = self.queryset_include_removed
        else:
            qs = self.queryset

        if self.request.method == "GET":
            # Prefetch Dataset.dataset_versions.datasets to DatasetVersions._datasets
            # but only for read-only requests to avoid having to invalidate the cached value
            qs = qs.prefetch_related(
                Prefetch(
                    "dataset_versions__datasets",
                    queryset=Dataset.all_objects.order_by("-version").prefetch_related(
                        "draft_of", "next_draft"
                    ),
                    to_attr="_datasets",
                )
            )

        qs = self.access_policy.scope_queryset(self.request, qs)
        return qs

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        """Create a new version of a published dataset."""
        dataset: Dataset = self.get_object()
        new_version = dataset.create_new_version()
        serializer = self.get_serializer(new_version)
        data = serializer.data
        new_version.signal_update(created=True)
        return response.Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create-draft")
    def create_draft(self, request, pk=None):
        """Create a draft dataset from a published dataset.

        The changes in the draft can be applied to the
        published dataset using the publish endpoint of the draft.
        """
        dataset: Dataset = self.get_object()
        draft = dataset.create_new_draft()
        data = self.get_serializer(draft).data
        draft.signal_update(created=True)
        return response.Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a dataset.

        - If dataset is a new draft, changes its state to "published".
        - If dataset is a draft of an existing published dataset,
          updates the published dataset with changes from the draft
          and deletes the draft.
        """
        dataset: Dataset = self.get_object()
        published_dataset = dataset.publish()
        data = self.get_serializer(published_dataset).data
        published_dataset.signal_update()
        return response.Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        dataset: Dataset = self.get_object()
        versions = dataset.all_revisions()
        serializer = self.get_serializer(versions, many=True)
        return response.Response(serializer.data)

    @swagger_auto_schema(responses={200: ContactResponseSerializer})
    @action(detail=True, methods=["POST"])
    def contact(self, request, pk=None):
        """Send email to dataset actors with specific role."""
        dataset: Dataset = self.get_object()
        serializer = ContactSerializer(data=request.data, context={"dataset": dataset})
        serializer.is_valid(raise_exception=True)
        mail_count = serializer.save()
        response_msg = ContactResponseSerializer(instance={"recipient_count": mail_count}).data
        return response.Response(response_msg, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: ContactRolesSerializer})
    @contact.mapping.get
    def contact_roles(self, request, pk=None):
        """Determine for each role if there are any email addresses for that role."""
        dataset: Dataset = self.get_object()
        serializer = ContactRolesSerializer(instance=dataset)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"])
    def convert_from_legacy(self, request):
        """Convert V1 or V2 dataset json into V3 json format.

        Accepts a V1 or V2 dataset json as the request body.
        Dataset fields are mapped to V3 format and the resulting dataset
        json is validated and then returned. If any errors found are found,
        the response will contain an additional "errors" object
        describing the errrors.

        Note that no permission checking is done and the dataset json
        may need additional changes to be ready for publishing.
        """
        data = None
        errors = {}
        with transaction.atomic():
            try:
                ensure_dict(request.data)
                try:
                    converter = LegacyDatasetConverter(
                        dataset_json=request.data, convert_only=True
                    )
                    data = omit_empty(converter.convert_dataset(), recurse=True)
                    if invalid := converter.get_invalid_values_by_path():
                        errors["invalid"] = invalid
                    if fixed := converter.get_fixed_values_by_path():
                        errors["fixed"] = fixed
                    serializer = LegacyDatasetUpdateSerializer(
                        data=data, context={"dataset": None}
                    )
                    serializer.is_valid(raise_exception=True)
                except serializers.ValidationError as e:
                    if data:
                        detail = e.detail
                        if not isinstance(e.detail, dict):
                            detail = {"error": detail}
                        errors.update(detail)
                    else:
                        raise e
                except (AttributeError, ValueError) as e:
                    # Catch unhandled cases where input data has wrong type
                    logger.warning(f"convert_from_legacy failed: {e}")
                    return response.Response(
                        "There was an error converting the dataset.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            finally:
                transaction.set_rollback(True)  # Ensure no side effects are left in DB
        if errors:
            data["errors"] = errors
        return response.Response(data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise NotAuthenticated("You must be authenticated to perform this action.")

        catalog: DataCatalog = serializer._validated_data["data_catalog"]
        if catalog and not DataCatalogAccessPolicy().query_object_permission(
            user=self.request.user, object=catalog, action="<op:create_dataset>"
        ):
            raise exceptions.PermissionDenied(
                "You are not allowed to create datasets in this data catalog."
            )
        dataset: Dataset = serializer.save(system_creator=self.request.user)
        dataset.signal_update(created=True)

    def perform_update(self, serializer):
        dataset: Dataset = serializer.save()
        dataset.signal_update()

    @action(detail=False)
    def aggregates(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = aggregate_queryset(queryset)
        return response.Response(aggregates, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        """Called by 'destroy' action."""
        flush = self.query_params["flush"]
        if flush and not DatasetAccessPolicy().query_object_permission(
            user=self.request.user, object=instance, action="<op:flush>"
        ):
            raise exceptions.PermissionDenied()
        instance.delete(soft=not flush)

    def get_extra_action_url_map(self):
        url_map = super().get_extra_action_url_map()

        if self.detail:
            url_map["Preservation"] = reverse(
                "dataset-preservation-detail",
                self.args,
                {"dataset_pk": self.kwargs["pk"]},
                request=self.request,
            )

        return url_map


class DatasetDirectoryViewSet(DirectoryViewSet):
    """API for browsing directories of a dataset."""

    # Omit dataset-specific parameters from API, set them manually for the view
    query_serializers = [
        {
            "class": DirectoryCommonQueryParams,
        }
    ]

    def validate_query_params(self):
        """Parse view query parameters."""
        super().validate_query_params()

        # Dataset id comes from route, file storage is determined from dataset
        dataset_id = self.kwargs["dataset_id"]
        params = {}
        params["dataset"] = dataset_id
        params["exclude_dataset"] = False
        params["include_all"] = False
        try:
            file_set = FileSet.objects.get(dataset_id=dataset_id)
            storage = file_set.storage
            params["storage_id"] = storage.id
        except FileSet.DoesNotExist:
            raise exceptions.NotFound()
        self.query_params.update(params)

    @swagger_auto_schema(responses={200: DirectorySerializer})
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)


class DatasetFilesViewSet(BaseFileViewSet):
    """API for listing dataset files."""

    filterset_class = FileCommonFilterset

    def get_queryset(self):
        # path parameters are not available on drf-yasg inspection
        if getattr(self, "swagger_fake_view", False):
            return File.objects.none()

        dataset_id = self.kwargs["dataset_id"]
        files = super().get_queryset()
        file_set: FileSet
        try:
            file_set = FileSet.objects.get(dataset=dataset_id)
        except FileSet.DoesNotExist:
            return files.none()
        return files.filter(file_sets=file_set.id)
