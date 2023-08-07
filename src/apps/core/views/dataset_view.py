# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models.catalog_record import Dataset, FileSet, DatasetActor
from apps.core.serializers import DatasetSerializer, FileSetSerializer
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
    data_catalog_id = filters.CharFilter(
        field_name="data_catalog__id",
        max_length=512,
        lookup_expr="icontains",
        label="data-catalog identifier",
        help_text="filter with substring from data-catalog identifier",
    )
    data_catalog_title = filters.CharFilter(
        field_name="data_catalog__title",
        max_length=512,
        lookup_expr="icontains",
        label="data-catalog title",
    )
    person = filters.CharFilter(
        field_name="actors__actor__person", max_length=512, lookup_expr="icontains", label="person"
    )
    organization_name = filters.CharFilter(
        field_name="actors__actor__organization__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="organization name",
    )
    metadata_owner_organization = filters.CharFilter(
        field_name="metadata_owner__organization",
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner organization",
    )
    metadata_owner_user = filters.CharFilter(
        field_name="metadata_owner__user__username",
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner user",
    )
    state = filters.ChoiceFilter(choices=Dataset.StateChoices.choices, label="state")
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )


class DatasetViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetSerializer
    queryset = Dataset.objects.prefetch_related(
        "data_catalog",
        "field_of_science",
        "language",
        "theme",
    )

    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "delete", "options"]

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
        try:
            file_set = FileSet.objects.get(dataset_id=dataset_id)
            file_storage = file_set.file_storage
            params["file_storage_id"] = file_storage.id
        except FileSet.DoesNotExist:
            raise exceptions.NotFound()
        return params

    @swagger_auto_schema(
        query_serializer=DirectoryCommonQueryParams,
        responses={200: DirectorySerializer},
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @swagger_auto_schema(
        query_serializer=DirectoryCommonQueryParams,
        responses={200: DirectorySerializer},
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)


class DatasetFileSetViewSet(viewsets.ViewSet):
    """API for listing and updating dataset files."""

    http_method_names = ["get", "post"]
    lookup_field = "storage_service"

    def get_dataset(self):
        try:
            dataset_id = self.kwargs["dataset_id"]
            return Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            raise exceptions.NotFound()

    def list(self, request, *args, **kwargs):
        dataset = self.get_dataset()
        file_set: FileSet
        try:
            file_set = dataset.file_set
        except FileSet.DoesNotExist:
            raise exceptions.NotFound()
        serializer = FileSetSerializer(instance=file_set)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        dataset = self.get_dataset()
        serializer = FileSetSerializer(
            data=request.data,
            context={"dataset": dataset},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        dataset.save()  # update dataset modification date
        return Response(serializer.data)


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
