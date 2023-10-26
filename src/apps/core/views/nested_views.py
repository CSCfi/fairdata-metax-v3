from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.core.mixins import DatasetNestedViewSetMixin
from apps.core.serializers import (
    AccessRightsModelSerializer,
    DatasetActorModelSerializer,
    ProvenanceModelSerializer,
)


class ProvenanceFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )
    description = filters.CharFilter(
        field_name="description__values",
        max_length=512,
        lookup_expr="icontains",
        label="description",
    )
    outcome_description = filters.CharFilter(
        field_name="outcome_description__values",
        max_length=512,
        lookup_expr="icontains",
        label="outcome description",
    )
    dataset__id = filters.CharFilter(
        field_name="dataset__id",
        max_length=512,
        lookup_expr="icontains",
        label="dataset id",
    )
    spatial__reference__url = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="spatial url",
    )
    spatial__reference__pref_label = filters.CharFilter(
        field_name="spatial__reference__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="Spatial location name",
    )
    spatial__full_address = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="Spatial location address",
    )
    spatial__geographic_name = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="Spatial geographic name",
    )
    is_associated_with__actor__organization__pref_label = filters.CharFilter(
        field_name="is_associated_with__actor__organization__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="Associated organization name",
    )
    is_associated_with__actor__person = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="Associated person name",
    )
    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )


class ProvenanceViewSet(DatasetNestedViewSetMixin):
    serializer_class = ProvenanceModelSerializer
    filterset_class = ProvenanceFilter


@swagger_auto_schema(operation_description="DatasetActor viewset")
class DatasetActorViewSet(DatasetNestedViewSetMixin):
    serializer_class = DatasetActorModelSerializer
    filter_backends = (filters.DjangoFilterBackend,)


class AccessRightsViewSet(DatasetNestedViewSetMixin):
    serializer_class = AccessRightsModelSerializer
    filter_backends = (filters.DjangoFilterBackend,)
