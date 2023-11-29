# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging
from typing import Optional

from django.core.exceptions import FieldError
from django.http import Http404
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.openapi import Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, response, status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.reverse import reverse
from watson import search

from apps.common.serializers.serializers import (
    FlushQueryParamsSerializer,
    IncludeRemovedQueryParamsSerializer,
)
from apps.common.views import CommonModelViewSet
from apps.core.models.catalog_record import Dataset, FileSet
from apps.core.models.preservation import Preservation
from apps.core.permissions import DatasetAccessPolicy
from apps.core.serializers import DatasetSerializer
from apps.core.serializers.dataset_allowed_actions import (
    DatasetAllowedActionsQueryParamsSerializer,
)
from apps.core.serializers.dataset_serializer import DatasetRevisionsQueryParamsSerializer
from apps.files.models import File
from apps.files.serializers import DirectorySerializer
from apps.files.views.directory_view import DirectoryCommonQueryParams, DirectoryViewSet
from apps.files.views.file_view import BaseFileViewSet, FileCommonFilterset

logger = logging.getLogger(__name__)


class DatasetFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title__values",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )
    data_catalog__id = filters.CharFilter(
        max_length=512,
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
    actors__actor__person__name = filters.CharFilter(
        max_length=512, lookup_expr="icontains", label="person name"
    )
    actors__actor__organization__pref_label = filters.CharFilter(
        field_name="actors__actor__organization__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="organization name",
    )
    metadata_owner__organization = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner organization",
    )
    metadata_owner__user__username = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner user",
    )
    persistent_identifier = filters.CharFilter(
        max_length=255,
        lookup_expr="exact",
        label="persistent identifier",
    )
    state = filters.ChoiceFilter(choices=Dataset.StateChoices.choices, label="state")
    preservation__contract = filters.CharFilter(
        max_length=512,
        label="preservation contract",
        lookup_expr="icontains",
        field_name="preservation__contract",
    )
    preservation__state = filters.MultipleChoiceFilter(
        choices=Preservation.PreservationState.choices,
        label="preservation_state",
        field_name="preservation__state",
    )
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )
    search = filters.CharFilter(method="search_dataset")

    def search_dataset(self, queryset, name, value):
        return search.filter(queryset, value)

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
            "actions": ["list", "retrieve"],
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
        "access_rights",
        "actors",
        "data_catalog",
        "field_of_science",
        "file_set",
        "language",
        "metadata_owner",
        "other_identifiers__identifier_type",
        "other_identifiers",
        "preservation",
        "provenance__is_associated_with",
        "provenance__spatial__reference",
        "provenance__spatial",
        "provenance__event_outcome",
        "provenance",
        "spatial__provenance",
        "spatial__reference",
        "spatial",
        "theme",
        "other_versions",
    )

    queryset = Dataset.available_objects.prefetch_related(*prefetch_fields)
    queryset_include_removed = Dataset.all_objects.prefetch_related(*prefetch_fields)

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]

    def get_object(self):
        queryset = self.get_queryset()

        try:
            obj = queryset.get(legacydataset__dataset_json__identifier=self.kwargs["pk"])
            self.check_object_permissions(self.request, obj)
            return obj
        except (Dataset.DoesNotExist, FieldError):
            return super().get_object()

    @action(detail=True, url_path="metadata-download", renderer_classes=[JSONRenderer])
    def metadata_download(self, request, pk=None):
        try:
            obj = self.get_object()
        except Http404:
            return response.Response("Dataset not found.", status=404, content_type="text/plain")

        serializer = self.serializer_class
        serializer_context = self.get_serializer_context()
        extension = "json"

        if request.query_params.get("format") == ("datacite" or "fairdata_datacite"):
            # serializer = serializer for datacite xml
            extension = "xml"

        return response.Response(
            serializer(obj, context=serializer_context).data,
            headers={"Content-Disposition": f"attachment; filename={pk}-metadata.{extension}"},
        )

    def get_queryset(self):
        include_all_datasets = self.query_params.get("include_removed") or self.query_params.get(
            "flush"
        )
        if include_all_datasets:
            return self.access_policy.scope_queryset(self.request, self.queryset_include_removed)
        return self.access_policy.scope_queryset(self.request, self.queryset)

    @action(detail=True, methods=["post", "get"], url_path="new-version")
    def new_version(self, request, pk=None):
        if request.method == "POST":
            dataset = self.get_object()
            new_version, _ = Dataset.create_copy(dataset)
            serializer = self.get_serializer(new_version)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == "GET":
            dataset = self.get_object()
            next_version = dataset.next_version
            if next_version is None:
                return response.Response(status=status.HTTP_404_NOT_FOUND)
            else:
                serializer = self.get_serializer(next_version)
                return response.Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        dataset: Dataset = self.get_object()
        serializer: Optional[DatasetSerializer]
        latest_published = self.query_params.get("latest_published")
        published_version = self.query_params.get("published_revision")
        all_published_versions = self.query_params.get("all_published_revisions")
        if latest_published:
            if published := dataset.latest_published_revision:
                serializer = self.get_serializer(published, many=False)
            else:
                return response.Response(status=status.HTTP_404_NOT_FOUND)
        elif published_version:
            version = dataset.get_revision(publication_number=published_version)
            if version:
                serializer = self.get_serializer(version)
            else:
                return response.Response(status=status.HTTP_404_NOT_FOUND)
        elif all_published_versions:
            versions = dataset.all_revisions(published_only=True)
            serializer = self.get_serializer(versions, many=True)
        else:
            serializer = self.get_serializer(dataset)
        return response.Response(serializer.data)

    def perform_destroy(self, instance):
        """Called by 'destroy' action."""
        flush = self.query_params["flush"]
        if flush and not DatasetAccessPolicy().query_object_permission(
            self.request, instance, action="<op:flush>"
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

    def get_params(self):
        """Parse view query parameters."""
        params_serializer = DirectoryCommonQueryParams(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        # dataset id comes from route, storage project is determined from dataset
        dataset_id = self.kwargs["dataset_id"]
        params["dataset"] = dataset_id
        params["exclude_dataset"] = False
        params["include_all"] = False
        try:
            file_set = FileSet.objects.get(dataset_id=dataset_id)
            storage = file_set.storage
            params["storage_id"] = storage.id
        except FileSet.DoesNotExist:
            raise exceptions.NotFound()
        return params

    @swagger_auto_schema(
        query_serializer=DirectoryCommonQueryParams,
        responses={200: DirectorySerializer},
    )
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
