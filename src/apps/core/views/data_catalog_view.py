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

from apps.core.models import DataCatalog
from apps.core.serializers import DataCatalogModelSerializer


class DataCatalogFilter(filters.FilterSet):
    class Meta:
        model = DataCatalog
        fields = (
            "dataset_versioning_enabled",
            "harvested",
            "dataset_schema",
        )

    title__values = filters.CharFilter(
        max_length=255, lookup_expr="icontains", label="title"
    )
    id = filters.CharFilter(max_length=255, lookup_expr="icontains")
    publisher__name__values = filters.CharFilter(
        max_length=255, lookup_expr="icontains", label="publisher name contains"
    )

    publisher__homepage__url = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    access_rights__description__values = filters.CharFilter(
        max_length=255,
        lookup_expr="icontains",
        label="access rights description contains",
    )
    access_rights__access_type__url = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    access_rights__access_type__pref_label__values = filters.CharFilter(
        max_length=255,
        lookup_expr="icontains",
        label="access rights access type preferred label contains",
    )
    publisher__homepage__title__values = filters.CharFilter(
        max_length=255,
        lookup_expr="icontains",
        label="publisher homepage title contains",
    )
    language__url = filters.CharFilter(max_length=255, lookup_expr="icontains")
    language__pref_label__values = filters.CharFilter(
        max_length=255,
        lookup_expr="icontains",
        label="language preferred label contains",
    )
    ordering = filters.OrderingFilter(fields=("created", "created"))


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List Data Catalogs"),
)
class DataCatalogView(viewsets.ModelViewSet):
    serializer_class = DataCatalogModelSerializer
    queryset = DataCatalog.objects.all()
    filterset_class = DataCatalogFilter
