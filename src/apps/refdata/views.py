from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters


class ReferenceDataPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


def get_filter_for_model(model):
    _model = model

    class ReferenceDataFilter(filters.FilterSet):
        class Meta:
            model = _model
            fields = ("pref_label", "url")

        url = filters.CharFilter(
            field_name="url",
            max_length=512,
            lookup_expr="icontains",
            label="url",
        )
        pref_label = filters.CharFilter(
            field_name="pref_label__values",
            max_length=255,
            lookup_expr="icontains",
            label="pref_label",
        )

        ordering = filters.OrderingFilter(
            fields=(
                ("created", "created"),
                ("modified", "modified"),
                ("url", "url"),
                ("pref_label__values", "pref_label"),
            )
        )
    return ReferenceDataFilter


def get_viewset_for_model(model):
    class ReferenceDataViewSet(viewsets.ReadOnlyModelViewSet):
        """Generic viewset for reference data objects."""

        serializer_class = model.get_serializer()
        queryset = model.available_objects.filter(
            is_reference_data=True
        ).prefetch_related("broader", "narrower")
        filter_backends = (filters.DjangoFilterBackend,)
        filterset_class = get_filter_for_model(model)
        pagination_class = ReferenceDataPagination

    return ReferenceDataViewSet
