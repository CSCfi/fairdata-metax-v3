import logging
from drf_yasg.utils import swagger_auto_schema
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from apps.core.models import DatasetLanguage
from apps.core.serializers import (
    DatasetPublisherModelSerializer,
    AccessRightsModelSerializer,
    DatasetLanguageModelSerializer,
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class PublisherViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetPublisherModelSerializer


class AccessRightsViewSet(viewsets.ModelViewSet):
    serializer_class = AccessRightsModelSerializer


class DatasetLanguageFilter(filters.FilterSet):
    class Meta:
        model = DatasetLanguage
        fields = ("title", "url")

    title = filters.CharFilter(
        field_name="title__values",
        max_length=255,
        lookup_expr="icontains",
        label="title",
    )
    url = filters.CharFilter(max_length=512, lookup_expr="icontains")
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("title__values", "title"),
            ("url", "url"),
        )
    )


@swagger_auto_schema(operation_description="Dataset language viewset")
class DatasetLanguageViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetLanguageModelSerializer
    queryset = DatasetLanguage.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DatasetLanguageFilter
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "put", "delete"]
