import logging
from drf_yasg.utils import swagger_auto_schema
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from apps.core.models import AccessRights
from apps.core.models.data_catalog import DatasetPublisher
from apps.core.serializers import (
    DatasetPublisherModelSerializer,
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
        field_name="homepage__url", max_length=512, lookup_expr="icontains", label="url"
    )
    name = filters.CharFilter(
        field_name="name__values", max_length=255, lookup_expr="icontains", label="name"
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("name__values", "name"),
            ("homepage__url", "url"),
            ("homepage__title__values", "homepage_title"),
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


class AccessRightsFilter(filters.FilterSet):
    class Meta:
        model = AccessRights
        fields = (
            "description",
            "access_type_url",
            "access_type_pref_label",
            "license_url",
            "license_pref_label",
        )

    description = filters.CharFilter(
        field_name="description__values",
        max_length=255,
        lookup_expr="icontains",
        label="description",
    )

    access_type_url = filters.CharFilter(
        field_name="access_type__url",
        max_length=512,
        lookup_expr="icontains",
        label="access_type_url",
    )

    access_type_pref_label = filters.CharFilter(
        field_name="access_type__pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="access_type_pref_label",
    )

    license_url = filters.CharFilter(
        field_name="license__url",
        max_length=512,
        lookup_expr="icontains",
        label="license_url",
    )

    license_pref_label = filters.CharFilter(
        field_name="license__pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="license_pref_label",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("description__values", "description"),
            ("access_type__url", "access_type_url"),
            ("access_type__pref_label__values", "access_type_pref_label"),
            ("license__url", "license_url"),
            ("license__pref_label__values", "license_pref_label"),
        )
    )
