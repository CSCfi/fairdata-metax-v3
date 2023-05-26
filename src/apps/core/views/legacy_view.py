from rest_framework import viewsets

from apps.core.serializers import LegacyDatasetModelSerializer
from apps.core.models import LegacyDataset
from django_filters import rest_framework as filters


class LegacyDatasetFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="dataset_json__research_dataset__title",
        lookup_expr="icontains",
        label="Research Dataset Title",
        max_length=512,
    )
    data_catalog = filters.CharFilter(
        field_name="dataset_json__data_catalog__identifier",
        lookup_expr="icontains",
        label="Data Catalog Identifier",
        max_length=512,
    )


class LegacyDatasetViewSet(viewsets.ModelViewSet):
    serializer_class = LegacyDatasetModelSerializer
    queryset = LegacyDataset.objects.all()
    lookup_field = "dataset_json__identifier"
    filterset_class = LegacyDatasetFilter
