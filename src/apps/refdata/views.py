from django_filters import rest_framework as filters

from apps.common.views import CommonReadOnlyModelViewSet


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
        deprecated = filters.BooleanFilter(lookup_expr="isnull", exclude=True)

        def filter_queryset(self, queryset):
            if self.form.cleaned_data.get("deprecated") is None:
                self.form.cleaned_data["deprecated"] = False  # Hide deprecated by default

            return super().filter_queryset(queryset)

    return ReferenceDataFilter


def get_viewset_for_model(model):
    class ReferenceDataViewSet(CommonReadOnlyModelViewSet):
        """Generic viewset for reference data objects."""

        serializer_class = model.get_serializer_class()
        queryset = model.available_objects.prefetch_related("broader", "narrower")
        filterset_class = get_filter_for_model(model)

    return ReferenceDataViewSet
