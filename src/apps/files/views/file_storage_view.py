# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from apps.files.models import FileStorage
from apps.files.serializers import FileStorageModelSerializer


class FileStorageFilter(filters.FilterSet):
    id = filters.CharFilter(max_length=255, lookup_expr="icontains")
    endpoint_url = filters.CharFilter(max_length=255, lookup_expr="icontains")
    endpoint_description = filters.CharFilter(max_length=255, lookup_expr="icontains")
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("endpoint_description", "endpoint_description"),
        )
    )


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List Data Storages"),
)
class FileStorageView(viewsets.ModelViewSet):
    serializer_class = FileStorageModelSerializer
    queryset = FileStorage.objects.all()
    filterset_class = FileStorageFilter
