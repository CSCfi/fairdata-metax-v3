from rest_framework import viewsets

from apps.core.mixins import DatasetNestedViewSetMixin
from apps.core.serializers import ProvenanceModelSerializer
from django_filters import rest_framework as filters


class ProvenanceFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title__values",
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
    dataset_id = filters.CharFilter(
        field_name="dataset__id",
        max_length=512,
        lookup_expr="icontains",
        label="dataset id",
    )
    spatial_url = filters.CharFilter(
        field_name="spatial__reference__url",
        max_length=512,
        lookup_expr="icontains",
        label="spatial url",
    )
    spatial_pref_label = filters.CharFilter(
        field_name="spatial__reference__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="Spatial location name",
    )
    spatial_full_address = filters.CharFilter(
        field_name="spatial__full_address",
        max_length=512,
        lookup_expr="icontains",
        label="Spatial location address",
    )
    spatial_geographic_name = filters.CharFilter(
        field_name="spatial__geographic_name",
        max_length=512,
        lookup_expr="icontains",
        label="Spatial geographic name",
    )
    associated_organization = filters.CharFilter(
        field_name="is_associated_with__actor__organization__pref_label__values",
        max_length=512,
        lookup_expr="icontains",
        label="Associated organization name",
    )
    associated_person = filters.CharFilter(
        field_name="is_associated_with__actor__person",
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dataset_pk"] = self.kwargs.get("dataset_pk")
        return context
