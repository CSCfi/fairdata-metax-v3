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
from rest_framework.response import Response

from apps.core.models.catalog_record import Dataset
from apps.core.serializers import DatasetFilesSerializer, DatasetSerializer
from apps.files.models import File, FileStorage
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
    http_method_names = ["get", "post", "put", "delete"]


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
            file_storage = Dataset.objects.get(id=dataset_id).file_storage
            if not file_storage:
                raise exceptions.NotFound()
            params["file_storage_id"] = file_storage.id
        except Dataset.DoesNotExist:
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


class DatasetFilesViewSet(BaseFileViewSet):
    """API for listing and updating dataset files."""

    filterset_class = FileCommonFilterset
    http_method_names = ["get", "post"]

    def get_queryset(self):
        # path parameters are not available on drf-yasg inspection
        if getattr(self, "swagger_fake_view", False):
            return File.objects.none()

        dataset_id = self.kwargs["dataset_id"]
        files = super().get_queryset()
        return files.filter(datasets=dataset_id)

    @swagger_auto_schema(
        request_body=DatasetFilesSerializer,
        responses={200: DatasetFilesSerializer},
    )
    def create(self, request, dataset_id):
        """Add or remove dataset files and update dataset-specific metadata."""
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            serializer = DatasetFilesSerializer(instance=dataset.files, data=self.request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        except Dataset.DoesNotExist:
            raise exceptions.NotFound()
