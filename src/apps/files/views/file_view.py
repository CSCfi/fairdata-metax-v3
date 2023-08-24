# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django import forms
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F, Q, QuerySet
from django.db.models.functions import Concat
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.files.helpers import get_file_metadata_model
from apps.files.models.file import File
from apps.files.serializers import DeleteWithProjectIdentifierSerializer, FileSerializer
from apps.files.serializers.fields import StorageServiceField
from apps.files.serializers.file_bulk_serializer import (
    BulkAction,
    FileBulkReturnValueSerializer,
    FileBulkSerializer,
)

logger = logging.getLogger(__name__)


class FileCommonFilterset(filters.FilterSet):
    """File attribute specific filters for files."""

    filename = filters.CharFilter(
        lookup_expr="icontains",
    )
    pathname = filters.CharFilter(method="pathname_filter")

    storage_identifier = filters.CharFilter()

    size_gt = filters.NumberFilter(field_name="size", lookup_expr="gt")
    size_lt = filters.NumberFilter(field_name="size", lookup_expr="lt")

    def pathname_filter(self, queryset, name, value):
        if value.endswith("/"):
            # Filtering by directory path, no need to include filename
            return queryset.filter(pathname__istartswith=value)
        return queryset.alias(pathname=Concat("pathname", "filename")).filter(
            pathname__istartswith=value
        )

    class Meta:
        model = File
        fields = ()


class FileFilterSet(FileCommonFilterset):
    """Add project and dataset filters to file filterset."""

    project = filters.CharFilter(
        field_name="storage__project",
        max_length=200,
    )
    storage_service = filters.CharFilter(
        field_name="storage__storage_service",
        max_length=255,
    )
    dataset = filters.UUIDFilter(field_name="file_sets__dataset_id")

    class Meta:
        model = File
        fields = ()


class FilesDatasetsQueryParamsSerializer(serializers.Serializer):
    files_datasets_key_choices = (("files", "files"), ("datasets", "datasets"))
    file_id_type_choices = (("id", "id"), ("storage_identifier", "storage_identifier"))

    keys = serializers.ChoiceField(choices=files_datasets_key_choices, default="files")
    keysonly = serializers.BooleanField(default=False)

    storage_service = StorageServiceField(default=None)
    file_id_type = serializers.ChoiceField(choices=file_id_type_choices, default="id")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        require_storage_service = attrs["file_id_type"] == "storage_identifier"
        if require_storage_service and not attrs.get("storage_service"):
            raise serializers.ValidationError(
                "Field storage_service is required when file_id_type=storage_identifier."
            )

        return attrs


class FilesDatasetsBodySerializer(serializers.ListSerializer):
    child = serializers.CharField()


class BaseFileViewSet(viewsets.ModelViewSet):
    """Basic read-only files view."""

    serializer_class = FileSerializer
    filterset_class = FileFilterSet
    http_method_names = ["get"]
    queryset = File.objects.prefetch_related("storage")

    def get_serializer(self, instance=None, *args, **kwargs):
        """Modified get_serializer that passes instance to get_serializer_context."""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context(instance))
        return serializer_class(instance, *args, **kwargs)

    def get_serializer_context(self, instance):
        """Add dataset file metadata to serializer context when listing files."""
        context = super().get_serializer_context()
        if self.request.method != "GET":
            return context

        # Get dataset id from kwargs (i.e. from url) or query parameters
        dataset_id = self.kwargs.get("dataset_id")
        if not dataset_id:
            dataset_id = forms.CharField(required=False).clean(
                self.request.query_params.get("dataset")
            )

        if dataset_id:
            # Convert single instance to list
            files = instance
            if not (isinstance(files, list) or isinstance(files, QuerySet)):
                files = [files]

            # Get file metadata objects as dict by file id
            file_metadata = (
                get_file_metadata_model()
                .objects.filter(file_set__dataset_id=dataset_id)
                .prefetch_related("file_type")
                .distinct("file_id")
                .in_bulk([f.id for f in files], field_name="file_id")
            )
            context["file_metadata"] = file_metadata
        return context


class FileViewSet(BaseFileViewSet):
    http_method_names = ["get", "post", "patch", "put", "delete"]

    # TODO: Restore files action (=convert removed files to "not removed", should not undeprecate datasets)

    @swagger_auto_schema(
        request_body=FilesDatasetsBodySerializer,
        query_serializer=FilesDatasetsQueryParamsSerializer,
    )
    @action(detail=False, methods=["post"])
    def datasets(self, request):
        """Annotate file or dataset identifiers with corresponding dataset or file identifiers.

        POST is used instead of GET because of query parameter length limitations for GET requests.
        The request body should contain an array of identifiers of type specified by the `keys`
        parameter.

        `keys=files` (default): Return object with file ids as keys, lists of dataset ids as values.

        `keys=datasets`: Return object with dataset ids as keys, lists of file ids as values.

        Keys with empty values are omitted.

        If `keysonly` is True (default is False), return only the keys as a list. This effectively removes keys that
        had no corresponding values (i.e. with `keys=files`, this returns only files that belong to a dataset).
        """

        params_serializer = FilesDatasetsQueryParamsSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        body_serializer = FilesDatasetsBodySerializer(data=self.request.data)
        body_serializer.is_valid(raise_exception=True)
        ids = body_serializer.validated_data

        # Support identifier in input/output, requires storage_service
        file_id_type = params["file_id_type"]

        # Allow limiting results to specific storage_service
        extra_filters = {}
        if storage_service := params["storage_service"]:
            extra_filters["storage__storage_service"] = storage_service

        try:
            # Fetch a queryset with dict in the format of {key: id, values: [id1, id2, ...]}
            queryset = []
            if params["keys"] == "files":  # keys are files, return file_id->dataset_id
                id_query = {f"{file_id_type}__in": ids}
                files = File.objects.filter(**id_query, **extra_filters)
                queryset = files.values(key=F(file_id_type)).exclude(file_sets__id=None)
                if not params["keysonly"]:
                    queryset = queryset.annotate(
                        values=ArrayAgg(
                            "file_sets__dataset__id",
                            filter=Q(file_sets__dataset__is_deprecated=False),
                        )
                    )
            else:  # keys are datasets, return dataset_id->file_id
                file_set_model = File.file_sets.rel.related_model
                file_sets = file_set_model.available_objects.filter(
                    dataset_id__in=ids, **extra_filters
                ).filter(dataset__is_deprecated=False)
                queryset = file_sets.values(key=F("dataset_id")).exclude(files__id=None)
                if not params["keysonly"]:
                    queryset = queryset.annotate(values=ArrayAgg(f"files__{file_id_type}"))
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)  # avoid 500 from invalid uuid

        if params["keysonly"]:
            return Response([v["key"] for v in queryset])
        else:
            return Response({str(v["key"]): v["values"] for v in queryset})

    def bulk_action(self, files, action):
        f = FileBulkSerializer(data=files, action=action)
        f.is_valid(raise_exception=True)
        f.save()
        return Response(f.data)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.INSERT),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="insert-many")
    def insert_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.INSERT)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.UPDATE),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="update-many")
    def update_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.UPDATE)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.UPSERT),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="upsert-many")
    def upsert_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.UPSERT)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.DELETE),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="delete-many")
    def delete_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.DELETE)

    @swagger_auto_schema(
        operation_description="Delete all files belonging to certain project",
        request_body=DeleteWithProjectIdentifierSerializer,
    )
    @action(detail=False, methods=["post"], url_path="delete-project")
    def delete_project(self, request):
        serializer = DeleteWithProjectIdentifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.delete_project()
        return Response(serializer.data)
