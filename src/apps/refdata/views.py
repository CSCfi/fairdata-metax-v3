from django_filters import rest_framework as filters
from rest_framework import viewsets


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
        queryset = model.available_objects.prefetch_related("broader", "narrower")
        filterset_class = get_filter_for_model(model)

    return ReferenceDataViewSet
