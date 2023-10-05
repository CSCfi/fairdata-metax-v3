# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions
from watson import search

from apps.common.views import CommonModelViewSet
from apps.core.models.catalog_record import Dataset, FileSet
from apps.core.serializers import DatasetSerializer
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
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )
    search = filters.CharFilter(method="search_dataset")

    def search_dataset(self, queryset, name, value):
        return search.filter(queryset, value)


class DatasetViewSet(CommonModelViewSet):
    serializer_class = DatasetSerializer
    queryset = Dataset.objects.prefetch_related(
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
        "provenance__is_associated_with",
        "provenance__spatial__reference",
        "provenance__spatial",
        "provenance__event_outcome",
        "provenance",
        "spatial__provenance",
        "spatial__reference",
        "spatial",
        "theme",
    )

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "options"]

    def get_object(self):
        queryset = self.get_queryset()

        try:
            obj = queryset.get(legacydataset__dataset_json__identifier=self.kwargs["pk"])
            self.check_object_permissions(self.request, obj)
            return obj
        except Dataset.DoesNotExist:
            return super().get_object()


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
