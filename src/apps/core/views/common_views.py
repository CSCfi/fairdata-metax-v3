import logging
from drf_yasg.utils import swagger_auto_schema
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from apps.core.models import DatasetLanguage
from apps.core.models.data_catalog import DatasetPublisher
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


class DatasetPublisherFilter(filters.FilterSet):
    class Meta:
        model = DatasetPublisher
        fields = ("name", "url", "homepage_title")

    homepage_title = filters.CharFilter(
        field_name="homepage__title__values",
        max_length=255,
        lookup_expr="icontains",
        label="homepage_title",
    )
    url = filters.CharFilter(
        field_name="homepage__url",
        max_length=512,
        lookup_expr="icontains",
        label="url"
    )
    name = filters.CharFilter(
        field_name="name__values",
        max_length=255,
        lookup_expr="icontains",
        label="name"
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("name__values", "name"),
            ("homepage__url", "url"),
            ("homepage__title__values", "homepage_title")
        )
    )


@swagger_auto_schema(operation_description="Publisher viewset")
class PublisherViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetPublisherModelSerializer
    queryset = DatasetPublisher.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DatasetPublisherFilter
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "put", "delete"]


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
