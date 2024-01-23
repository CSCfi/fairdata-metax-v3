from django_filters import rest_framework as filters

from apps.common.views import CommonModelViewSet
from apps.core.models import LegacyDataset
from apps.core.permissions import LegacyDatasetAccessPolicy
from apps.core.serializers import LegacyDatasetModelSerializer


class LegacyDatasetFilter(filters.FilterSet):
    dataset_json__research_dataset__title = filters.CharFilter(
        lookup_expr="icontains",
        label="Research Dataset Title",
        max_length=512,
    )
    dataset_json__data_catalog__identifier = filters.CharFilter(
        lookup_expr="icontains",
        label="Data Catalog Identifier",
        max_length=512,
    )


class LegacyDatasetViewSet(CommonModelViewSet):
    serializer_class = LegacyDatasetModelSerializer
    queryset = LegacyDataset.available_objects.all()
    filterset_class = LegacyDatasetFilter
    access_policy = LegacyDatasetAccessPolicy
