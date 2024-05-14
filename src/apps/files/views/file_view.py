# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from django import forms
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.filters import VerboseChoiceFilter
from apps.common.helpers import cachalot_toggle, get_filter_openapi_parameters
from apps.common.serializers import DeleteListReturnValueSerializer, FlushQueryParamsSerializer
from apps.common.serializers.serializers import IncludeRemovedQueryParamsSerializer
from apps.common.views import CommonModelViewSet
from apps.files.helpers import get_file_metadata_model
from apps.files.models.file import File
from apps.files.permissions import FilesAccessPolicy
from apps.files.serializers import FileSerializer
from apps.files.serializers.fields import StorageServiceField
from apps.files.serializers.file_bulk_serializer import (
    BulkAction,
    FileBulkReturnValueSerializer,
    FileBulkSerializer,
)
from apps.files.signals import pre_files_deleted

logger = logging.getLogger(__name__)


class FileCommonFilterset(filters.FilterSet):
    """File attribute specific filters for files."""

    filename = filters.CharFilter(
        lookup_expr="icontains",
    )
    pathname = filters.CharFilter(method="pathname_filter")

    storage_identifier = filters.CharFilter()

    frozen__gt = filters.DateTimeFilter(field_name="frozen", lookup_expr="gt")

    def pathname_filter(self, queryset, name, value):
        if value.endswith("/"):
            # Filtering by directory path, no need to include filename
            return queryset.filter(directory_path__istartswith=value)
        return queryset.alias(pathname=Concat("directory_path", "filename")).filter(
            pathname__istartswith=value
        )

    class Meta:
        model = File
        fields = ()


class FileFilterSet(FileCommonFilterset):
    """Add project and dataset filters to file filterset."""

    csc_project = filters.CharFilter(
        field_name="storage__csc_project",
        max_length=200,
    )
    storage_service = VerboseChoiceFilter(
        field_name="storage__storage_service",
        choices=[(v, v) for v in settings.STORAGE_SERVICE_FILE_STORAGES],
    )

    dataset = filters.UUIDFilter(field_name="file_sets__dataset_id")

    class Meta:
        model = File
        fields = ()


class FileDeleteListFilterSet(FileFilterSet):
    """Add project and dataset filters to file filterset."""

    csc_project = filters.CharFilter(
        field_name="storage__csc_project", max_length=200, required=True
    )


class FilesDatasetsQueryParamsSerializer(serializers.Serializer):
    relations = serializers.BooleanField(
        default=False, help_text="List dataset relations per file"
    )
    storage_service = StorageServiceField(default=None)


class FilesDatasetsBodySerializer(serializers.ListSerializer):
    child = serializers.CharField()


class BaseFileViewSet(CommonModelViewSet):
    """Basic read-only files view."""

    serializer_class = FileSerializer
    filterset_class = FileFilterSet
    http_method_names = ["get"]
    queryset = File.available_objects.prefetch_related("storage")
    queryset_include_removed = File.all_objects.prefetch_related("storage")
    access_policy: FilesAccessPolicy = FilesAccessPolicy

    # Query serializer info for query_params and swagger generation
    query_serializers = [
        {
            "class": IncludeRemovedQueryParamsSerializer,
            "actions": ["list", "retrieve"],
        }
    ]

    def get_queryset(self):
        queryset = self.queryset
        if self.query_params.get("include_removed"):
            queryset = self.queryset_include_removed

        return self.access_policy.scope_queryset(
            self.request, queryset, dataset_id=self.get_dataset_id()
        )

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        pagination_enabled = self.paginator.pagination_enabled(request)
        with cachalot_toggle(pagination_enabled):
            return super().list(request, *args, **kwargs)

    def get_serializer(self, instance=None, *args, **kwargs):
        """Modified get_serializer that passes instance to get_serializer_context."""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context(instance))
        return serializer_class(instance, *args, **kwargs)

    def get_dataset_id(self):
        """Get dataset id from kwargs (i.e. from url) or query parameters."""
        dataset_id = self.kwargs.get("dataset_id")
        if not dataset_id and self.request:
            dataset_id = forms.CharField(required=False).clean(
                self.request.query_params.get("dataset")
            )
        return dataset_id

    def get_serializer_context(self, instance):
        """Add dataset file metadata to serializer context when listing files."""
        context = super().get_serializer_context()
        if self.request and self.request.method != "GET":
            return context

        if dataset_id := self.get_dataset_id():
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


class FileBulkQuerySerializer(serializers.Serializer):
    ignore_errors = serializers.BooleanField(
        default=False, help_text=_("Commit changes and return 200 even if there are errors.")
    )


class FileViewSet(BaseFileViewSet):
    http_method_names = ["get", "post", "patch", "put", "delete"]

    # TODO: Restore files action (=convert removed files to "not removed", should not undeprecate datasets)

    query_serializers = BaseFileViewSet.query_serializers + [
        {
            "class": FilesDatasetsQueryParamsSerializer,
            "actions": ["datasets"],
        },
        {
            "class": FileBulkQuerySerializer,
            "actions": ["post_many", "patch_many", "put_many", "delete_many"],
        },
        {"class": FlushQueryParamsSerializer, "actions": ["destroy_list"]},
    ]

    @property
    def filterset_class(self):
        if self.action == "destroy_list":
            # DELETE on list requires project to be set
            return FileDeleteListFilterSet
        else:
            return FileFilterSet

    @swagger_auto_schema(
        request_body=FilesDatasetsBodySerializer,
    )
    @action(detail=False, methods=["post"])
    def datasets(self, request):
        """Return datasets belonging to files.

        The request body should contain an array of file identifiers.
        By default, the file identifiers are internal Metax `id` values.
        If `storage_service` is set, the identifiers are `storage_identifier`
        values specific to that storage service. The file identifiers in
        the response will be of the same type as the input identifiers.

        `relations=false` (default): Return list of dataset ids.

        `relations=true`: Return object with a list of dataset ids
        for each file identifier. Files with no datasets are omitted.

        `storage_service`: List only files in specific storage service, and
        use `storage_identifier` as file identifier in both input and output.


        POST is used instead of GET because of query parameter length limitations for GET requests.
        """

        body_serializer = FilesDatasetsBodySerializer(data=self.request.data)
        body_serializer.is_valid(raise_exception=True)
        ids = body_serializer.validated_data

        # File identifiers are metax internal ids unless storage_service is defined
        file_id_type = "id"

        # Allow limiting results to specific storage_service
        params = self.query_params
        storage_filter = Q()
        if storage_service := params["storage_service"]:
            file_id_type = "storage_identifier"
            storage_filter = Q(storage__storage_service=storage_service)

        try:
            if params["relations"]:
                # Return dict of file ids -> list of dataset ids
                file_id_filter = Q(**{f"{file_id_type}__in": ids})
                queryset = File.objects.filter(
                    file_id_filter, storage_filter, file_sets__isnull=False
                ).values(key=F(file_id_type))
                queryset = queryset.annotate(
                    values=ArrayAgg(
                        "file_sets__dataset_id",
                        filter=Q(file_sets__dataset__deprecated__isnull=True),
                        default=Value([]),
                    )
                )
                return Response({str(v["key"]): v["values"] for v in queryset})
            else:
                # Return list of dataset ids
                file_id_filter = Q(**{f"files__{file_id_type}__in": ids})
                file_set_model = File.file_sets.rel.related_model
                queryset = (
                    file_set_model.objects.filter(file_id_filter, storage_filter)
                    .values_list("dataset__id", flat=True)
                    .distinct()
                )
                return Response(queryset)

        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)  # avoid 500 from invalid uuid

    def bulk_action(self, files, action):
        ignore_errors = self.query_params["ignore_errors"]
        serializer = FileBulkSerializer(data=files, action=action, ignore_errors=ignore_errors)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        status = 200
        if serializer.data.get("failed") and not ignore_errors:
            status = 400
        return Response(serializer.data, status=status)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.INSERT),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="post-many")
    def post_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.INSERT)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.UPDATE),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="patch-many")
    def patch_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.UPDATE)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.UPSERT),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="put-many")
    def put_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.UPSERT)

    @swagger_auto_schema(
        request_body=FileBulkSerializer(action=BulkAction.DELETE),
        responses={200: FileBulkReturnValueSerializer()},
    )
    @action(detail=False, methods=["post"], url_path="delete-many")
    def delete_many(self, request):
        return self.bulk_action(request.data, action=BulkAction.DELETE)

    @swagger_auto_schema(
        operation_id="v3_files_delete_list",
        manual_parameters=get_filter_openapi_parameters(FileDeleteListFilterSet),
        responses={200: DeleteListReturnValueSerializer()},
    )
    def destroy_list(self, *args, **kwargs):
        """Delete files matching query parameters.

        The `csc_project` parameter is required. If no `storage_service` is defined,
        matching files from all storage services are deleted.

        By default the files are flagged as removed.
        When flush is enabled, the files are removed from the database.
        """

        flush = self.query_params["flush"]
        queryset: QuerySet
        if flush:
            queryset = File.all_objects
        else:
            queryset = File.available_objects
        queryset = self.filter_queryset(queryset)

        count = queryset.count()

        pre_files_deleted.send(sender=File, queryset=queryset)

        queryset.delete()

        return Response(DeleteListReturnValueSerializer(instance={"count": count}).data, 200)

    def perform_destroy(self, instance):
        pre_files_deleted.send(sender=File, queryset=File.objects.filter(id=instance.id))
        return super().perform_destroy(instance)
