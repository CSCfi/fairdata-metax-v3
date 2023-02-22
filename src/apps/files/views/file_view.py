# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, serializers
from rest_framework.pagination import LimitOffsetPagination
from drf_yasg.utils import swagger_auto_schema

from django_filters import rest_framework as filters
from django.db.models.functions import Concat
from django.db.models import Q, F
from django.contrib.postgres.aggregates import ArrayAgg

from apps.files.models.file import File
from apps.files.serializers.file_serializer import (
    FileSerializer,
    FileCreateQueryParamsSerializer,
)


class FilePagination(LimitOffsetPagination):
    default_limit = 100


class CreateListModelMixin:
    def get_serializer(self, *args, **kwargs):
        """Use list serializer when provided with a list of files."""
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True
        return super().get_serializer(*args, **kwargs)


class FileCommonFilterset(filters.FilterSet):
    """File attribute specific filters for files."""

    file_name = filters.CharFilter(
        lookup_expr="icontains",
    )
    directory_path = filters.CharFilter(
        lookup_expr="istarts_with",
    )
    file_path = filters.CharFilter(method="file_path_filter")

    byte_size_gt = filters.NumberFilter(field_name="byte_size", lookup_expr="gt")
    byte_size_lt = filters.NumberFilter(field_name="byte_size", lookup_expr="lt")

    def file_path_filter(self, queryset, name, value):
        return queryset.alias(file_path=Concat("directory_path", "file_name")).filter(
            file_path__istartswith=value
        )

    class Meta:
        model = File
        fields = ()


class FileFilterSet(FileCommonFilterset):
    """Add project and dataset filters to file filterset."""

    project_identifier = filters.CharFilter(
        field_name="storage_project__project_identifier",
        max_length=200,
    )
    file_storage = filters.CharFilter(
        field_name="storage_project__file_storage",
        max_length=255,
    )
    dataset = filters.UUIDFilter(field_name="datasets__id")

    class Meta:
        model = File
        fields = ()


files_datasets_key_choices = (("files", "files"), ("datasets", "datasets"))


class FilesDatasetsQueryParamsSerializer(serializers.Serializer):
    keys = serializers.ChoiceField(choices=files_datasets_key_choices, default="files")
    keysonly = serializers.BooleanField(default=False)


class FilesDatasetsBodySerializer(serializers.ListSerializer):
    child = serializers.CharField()


class FileViewSet(CreateListModelMixin, viewsets.ModelViewSet):
    serializer_class = FileSerializer
    pagination_class = FilePagination
    filterset_class = FileFilterSet
    http_method_names = ["get", "post", "patch", "put", "delete"]
    queryset = File.objects.prefetch_related("storage_project")

    @swagger_auto_schema(query_serializer=FileCreateQueryParamsSerializer)
    def create(
        self, *args, **kwargs
    ):  # TODO: Instead of this, use separate actions for bulk operations
        return super().create(*args, **kwargs)

    # TODO: Bulk update, bulk patch, bulk delete

    # TODO: Restore files action (=convert removed files to "not removed", should not undeprecate datasets)

    @swagger_auto_schema(request_body=FilesDatasetsBodySerializer)
    @action(detail=False, methods=["post"], url_path="datasets")
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

        params_serializer = FilesDatasetsQueryParamsSerializer(
            data=self.request.query_params
        )
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        body_serializer = FilesDatasetsBodySerializer(data=self.request.data)
        body_serializer.is_valid(raise_exception=True)
        ids = body_serializer.validated_data

        # Fetch a queryset with dict in the format of {key: id, values: [id1, id2, ...]}
        queryset = []
        if params["keys"] == "files":  # keys are files
            files = File.objects.filter(id__in=ids)
            queryset = files.values(key=F("id")).exclude(datasets__id=None)
            if not params["keysonly"]:
                queryset = queryset.annotate(
                    values=ArrayAgg(
                        "datasets__id", filter=Q(datasets__is_deprecated=False)
                    )
                )
        else:  # keys are datasets
            datasets = File.datasets.rel.related_model.available_objects.filter(
                id__in=ids
            ).filter(is_deprecated=False)
            queryset = datasets.values(key=F("id")).exclude(files__id=None)
            if not params["keysonly"]:
                queryset = queryset.annotate(values=ArrayAgg("files__id"))

        if params["keysonly"]:
            return Response([v["key"] for v in queryset])
        else:
            return Response({str(v["key"]): v["values"] for v in queryset})