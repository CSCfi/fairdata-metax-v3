# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
from rest_framework import viewsets

from apps.core.models import DataCatalog

from apps.core.serializers.data_catalog_serializer import DataCatalogModelSerializer


from django_filters import rest_framework as filters


class DataCatalogFilter(filters.FilterSet):
    class Meta:
        model = DataCatalog
        fields = (
            "title",
            "dataset_versioning_enabled",
            "harvested",
            "research_dataset_schema",
        )

    title = filters.CharFilter(max_length=255, lookup_expr="icontains")
    id = filters.CharFilter(max_length=255, lookup_expr="icontains")
    publisher__name = filters.CharFilter(max_length=255, lookup_expr="icontains")
    publisher__homepage__url = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    access_rights__description = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    access_rights__access_type__url = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    access_rights__access_type__title = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    publisher__homepage__title = filters.CharFilter(
        max_length=255, lookup_expr="icontains"
    )
    language__url = filters.CharFilter(max_length=255, lookup_expr="icontains")
    language__title = filters.CharFilter(max_length=255, lookup_expr="icontains")
    ordering = filters.OrderingFilter(fields=("created", "created"))


class DataCatalogView(viewsets.ModelViewSet):
    serializer_class = DataCatalogModelSerializer
    queryset = DataCatalog.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DataCatalogFilter
