# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging
import operator
from datetime import datetime, timezone
from enum import Enum
from functools import reduce
from typing import List

import pytz
from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.db.models import OuterRef, Prefetch, Q, QuerySet, Value, prefetch_related_objects
from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.http import parse_http_date
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.fields import CSVWidget
from drf_yasg.openapi import TYPE_STRING, Parameter, Response, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, response, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import JSONRenderer
from rest_framework.reverse import reverse
from watson import search

from apps.common.filters import MultipleCharFilter, VerboseChoiceFilter
from apps.common.helpers import ensure_dict, omit_empty
from apps.common.profiling import count_queries
from apps.common.serializers.serializers import (
    FieldsQueryParamsSerializer,
    FlushQueryParamsSerializer,
    IncludeRemovedQueryParamsSerializer,
)
from apps.common.views import CommonModelViewSet
from apps.core.cache import DatasetSerializerCache
from apps.core.models.catalog_record import Dataset, FileSet
from apps.core.models.catalog_record.dataset import DatasetVersions
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
from apps.core.serializers.dataset_metrics_serializer import DatasetMetricsQueryParamsSerializer
from apps.core.serializers.dataset_serializer import (
    DatasetRevisionsQueryParamsSerializer,
    ExpandCatalogQueryParamsSerializer,
    LatestVersionQueryParamsSerializer,
)
from apps.core.serializers.legacy_serializer import LegacyDatasetConversionValidationSerializer
from apps.core.services import MetaxV2Client, PIDMSClient
from apps.core.views.common_views import DefaultValueOrdering
from apps.files.models import File
from apps.files.serializers import DirectorySerializer
from apps.files.views.directory_view import DirectoryCommonQueryParams, DirectoryViewSet
from apps.files.views.file_view import BaseFileViewSet, FileCommonFilterset
from apps.users.models import MetaxUser

from .dataset_aggregation import aggregate_queryset

logger = logging.getLogger(__name__)
serialized_datasets_cache = caches["serialized_datasets"]


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
        method="filter_preservation__state",
        label="preservation_state",
        field_name="preservation__state",
    )
    publishing_channels = VerboseChoiceFilter(
        choices=[("etsin", "etsin"), ("ttv", "ttv"), ("all", "all")],
        method="filter_publishing_channels",
        help_text="Filter datasets based on the publishing channels of the dataset's catalog. The default value is 'etsin'.",
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
            ("preservation__state", "preservation_state"),  # Needed for FDDPS
            ("id", "id"),  # Needed for FDDPS
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
            queryset=queryset,
            value=value,
            filter_param="access_rights__access_type__pref_label__values__icontains",
        )

    def filter_organization(self, queryset, name, value):
        result = queryset
        for group in value:
            union = reduce(
                operator.or_,
                (
                    (
                        Q(actors__organization__pref_label__values__icontains=x)
                        | Q(actors__organization__parent__pref_label__values__icontains=x)
                        | Q(actors__organization__parent__parent__pref_label__values__icontains=x)
                    )
                    for x in group
                ),
            )
            result = result.filter(union)
        return result.distinct()

    def filter_keyword(self, queryset, name, value):
        return self._filter_list(queryset, value, filter_param="keyword__icontains")

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
            queryset,
            value,
            filter_param="field_of_science__pref_label__values__icontains",
        )

    def filter_infrastructure(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="infrastructure__pref_label__values__icontains",
        )

    def filter_file_type(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="file_set__file_metadata__file_type__pref_label__values__icontains",
        )

    def filter_project(self, queryset, name, value):
        return self._filter_list(
            queryset, value, filter_param="projects__title__values__icontains"
        )

    def filter_publishing_channels(self, queryset, name, value):
        if value == "all":
            return queryset
        if value == "etsin":
            return queryset.filter(
                Q(data_catalog__publishing_channels__contains=["etsin"])
                | Q(data_catalog__isnull=True)
            )
        return queryset.filter(data_catalog__publishing_channels__contains=[value])

    def filter_preservation__state(self, queryset, name, value):
        states = value

        state_query = Q(preservation__state__in=states)

        # If dataset's preservation entry does not exist, it's considered
        # to have the default value -1 (NONE)
        if str(Preservation.PreservationState.NONE) in states:
            return queryset.filter(state_query | Q(preservation__isnull=True))

        return queryset.filter(state_query)

    def _filter_list(self, queryset: QuerySet, value: List[List[str]], filter_param: str):
        result = queryset
        for group in value:
            union = reduce(operator.or_, (Q(**{filter_param: x}) for x in group))
            result = result.filter(union)
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

    def filter_queryset(self, queryset):
        # Use "etsin" as the default publishing channel filter value
        if not self.form.cleaned_data["publishing_channels"]:
            self.form.cleaned_data["publishing_channels"] = "etsin"
        return super().filter_queryset(queryset)


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
        {"class": LatestVersionQueryParamsSerializer, "actions": ["list", "aggregates"]},
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
            "class": DatasetMetricsQueryParamsSerializer,
            "actions": ["retrieve", "list", "create", "update", "partial_update", "revisions"],
        },
        {
            "class": IncludeRemovedQueryParamsSerializer,
            "actions": [
                "list",
                "retrieve",
                "update",
                "partial_update",
                "contact",
                "contact_roles",
            ],
        },
        {
            "class": FlushQueryParamsSerializer,
            "actions": ["destroy"],
        },
        {
            "class": FieldsQueryParamsSerializer,
            "actions": ["list"],
        },
    ]
    access_policy = DatasetAccessPolicy
    serializer_class = DatasetSerializer

    queryset = Dataset.available_objects.prefetch_related(
        *Dataset.common_prefetch_fields
    ).annotate(is_prefetched=Value(True))
    queryset_include_removed = Dataset.all_objects.prefetch_related(
        *Dataset.common_prefetch_fields
    ).annotate(is_prefetched=Value(True))

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.query_params.get("latest_versions"):
            # Return only latest versions available for the current user
            available_datasets = self.get_queryset()
            latest_versions = available_datasets.order_by(
                "dataset_versions_id", "-created"
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
            qs = qs.prefetch_related(Dataset.get_versions_prefetch())

            if timestamp := self.request.META.get("HTTP_IF_MODIFIED_SINCE"):
                try:
                    date = datetime.fromtimestamp(parse_http_date(timestamp), timezone.utc)
                except Exception:
                    raise exceptions.ValidationError(
                        {
                            "headers": {
                                "If-Modified-Since": "Bad value. If-Modified-Since supports only RFC 2822 datetime format."
                            }
                        }
                    )
                if date:
                    qs = qs.filter(modified__gt=date)

        qs = self.access_policy.scope_queryset(self.request, qs)
        return qs

    def allow_cache(self) -> bool:
        """Disallow caching when include_nulls=True."""
        return not self.include_nulls

    def get_serializer(self, *args, cached_instances=[], cache_autocommit=True, **kwargs):
        serializer_cache = None
        if self.allow_cache():
            # Use cached fields for serialization of datasets in cached_instances
            serializer_cache = DatasetSerializerCache(
                cached_instances, autocommit=cache_autocommit
            )
        return super().get_serializer(*args, cache=serializer_cache, **kwargs)

    def apply_partial_prefetch(
        self, datasets: List[Dataset], serializer: DatasetSerializer, prefetches: list
    ):
        """Prefetch related objects with support for partial prefetch for cached datasets."""
        values = {}
        if cache := serializer.cache:
            values = cache.values
        uncached_datasets = [d for d in datasets if d.id not in values]
        cached_datasets = [d for d in datasets if d.id in values]

        # Do normal prefetch for datasets not in cache
        prefetch_related_objects(uncached_datasets, *prefetches)

        # For cached datasets, prefetch only uncached relations, e.g. draft_of, other_identifiers
        cached_fields = set(serializer.get_cached_field_sources())
        partial_prefetches = []  # Prefetches that are not in cached_fields
        for prefetch in prefetches:
            if type(prefetch) is str:
                prefix = prefetch.split("__", 1)[0]
                if prefix in cached_fields:
                    continue
            partial_prefetches.append(prefetch)
        prefetch_related_objects(cached_datasets, *partial_prefetches)

    def list(self, request, *args, **kwargs):
        """List datasets."""
        queryset = self.filter_queryset(self.get_queryset())

        # Defer prefetching until after pagination is done
        # and we know which datasets are in serialized datasets cache
        prefetches = queryset._prefetch_related_lookups
        queryset = queryset.prefetch_related(None)
        queryset = queryset.prefetch_related(*Dataset.permissions_prefetch_fields)

        page = self.paginate_queryset(queryset)

        datasets: List[Dataset]
        if page is None:
            datasets = queryset.all()
        else:
            datasets = page

        list_serializer = self.get_serializer(
            datasets, cached_instances=datasets, cache_autocommit=False, many=True
        )
        dataset_serializer: DatasetSerializer = list_serializer.child
        cache = dataset_serializer.cache
        if cache and settings.DEBUG_DATASET_CACHE:
            logger.info(f"Datasets in cache: {len(cache.values)}/{len(datasets)}")
        self.apply_partial_prefetch(datasets, list_serializer.child, prefetches)

        serialized_data = list_serializer.data  # Run serialization
        if cache:
            cache.commit_changed_to_source()  # Commit updated serializations to cache

        if page is None:
            return response.Response(serialized_data)
        else:
            return self.get_paginated_response(serialized_data)

    def _get_object_with_deferred_prefetch(self):
        """Get object without triggering prefetch."""
        queryset = self.get_queryset()

        # Defer prefetching until we know if dataset is in cache
        prefetches = queryset._prefetch_related_lookups
        queryset = queryset.prefetch_related(None)
        queryset = queryset.prefetch_related(*Dataset.permissions_prefetch_fields)

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj, prefetches

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single dataset. Modified for cache use."""
        instance, prefetches = self._get_object_with_deferred_prefetch()

        serializer: DatasetSerializer = self.get_serializer(instance, cached_instances=[instance])
        if (cache := serializer.cache) and settings.DEBUG_DATASET_CACHE:
            logger.info(f"Dataset in cache: {instance.id in cache.values}")

        self.apply_partial_prefetch([instance], serializer, prefetches)
        return response.Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        """Create a new version of a published dataset.

        The new version is created as a draft.
        """
        dataset: Dataset = self.get_object()
        new_version = dataset.create_new_version()
        serializer = self.get_serializer(new_version)
        data = serializer.data
        new_version.signal_update(created=True)

        if settings.METAX_V2_INTEGRATION_ENABLED:
            # New version is a initially a draft that is not synced to V2,
            # so V2 does not know it exists. Mark original as having been
            # updated in V3 to prevent creating more versions in V2.
            MetaxV2Client().update_api_meta(dataset)

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

    @action(detail=True, methods=["post"], url_path="create-preservation-version")
    def create_preservation_version(self, request, pk=None):
        """Create preservation version of a dataset in PAS process."""
        dataset: Dataset = self.get_object()
        new_version = dataset.create_preservation_version()
        serializer = self.get_serializer(new_version)
        data = serializer.data
        new_version.signal_update(created=True)
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
        dataset.api_version = 3
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

    @swagger_auto_schema(
        request_body=ContactSerializer(), responses={200: ContactResponseSerializer}
    )
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

    @swagger_auto_schema(request_body=Schema(type="object"), responses={200: DatasetSerializer})
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
                    serializer = LegacyDatasetConversionValidationSerializer(
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

    def _check_allow_create_datasets_in_catalog(self, catalog: DataCatalog):
        """Raise error if request user is not allowed to create datasets in the catalog."""
        if not DataCatalogAccessPolicy().query_object_permission(
            user=self.request.user, object=catalog, action="<op:create_dataset>"
        ):
            raise exceptions.PermissionDenied(
                "You are not allowed to create datasets in this data catalog."
            )

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise NotAuthenticated("You must be authenticated to perform this action.")

        catalog: DataCatalog = serializer._validated_data.get("data_catalog")
        if catalog:
            self._check_allow_create_datasets_in_catalog(catalog)
        dataset: Dataset = serializer.save(system_creator=self.request.user)
        dataset.signal_update(created=True)

    def perform_update(self, serializer):
        catalog: DataCatalog = serializer._validated_data.get("data_catalog")
        if catalog and not serializer.instance.data_catalog:
            # Setting catalog of a draft needs permission to create datasets in the catalog
            self._check_allow_create_datasets_in_catalog(catalog)
        dataset: Dataset = serializer.save()
        if (
            dataset.state == Dataset.StateChoices.PUBLISHED
            and dataset.pid_generated_by_fairdata
            and dataset.generate_pid_on_publish == "DOI"
        ):
            PIDMSClient().update_doi_dataset(dataset.id, dataset.persistent_identifier)
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
