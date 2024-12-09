# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.common.views import CommonModelViewSet
from apps.core.models import DataCatalog
from apps.core.permissions import DataCatalogAccessPolicy
from apps.core.serializers import DataCatalogModelSerializer


class DataCatalogFilter(filters.FilterSet):
    class Meta:
        model = DataCatalog
        fields = (
            "dataset_versioning_enabled",
            "is_external",
        )

    title = filters.CharFilter(
        max_length=255,
        lookup_expr="icontains",
        label="title__values",
    )
    id = filters.CharFilter(max_length=255, lookup_expr="icontains")
    publisher__name = filters.CharFilter(
        field_name="publisher__name__values",
        max_length=255,
        lookup_expr="icontains",
        label="publisher name contains",
    )

    publisher__homepage__url = filters.CharFilter(max_length=255, lookup_expr="icontains")
    description = filters.CharFilter(
        field_name="description__values",
        max_length=255,
        lookup_expr="icontains",
        label="access rights description contains",
    )
    publisher__homepage__title = filters.CharFilter(
        field_name="publisher__homepage__title__values",
        max_length=255,
        lookup_expr="icontains",
        label="publisher homepage title contains",
    )
    language__url = filters.CharFilter(max_length=255, lookup_expr="icontains")
    language__pref_label = filters.CharFilter(
        field_name="language__pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="language preferred label contains",
    )

    ordering = filters.OrderingFilter(fields=("created", "created"))


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List Data Catalogs"),
)
class DataCatalogView(CommonModelViewSet):
    serializer_class = DataCatalogModelSerializer
    queryset = DataCatalog.objects.all()
    filterset_class = DataCatalogFilter
    access_policy = DataCatalogAccessPolicy
