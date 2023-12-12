from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import serializers

from apps.actors.models import Organization
from apps.actors.serializers import OrganizationSerializer
from apps.common.views import CommonReadOnlyModelViewSet


class OrganizationFilterSet(filters.FilterSet):
    pref_label = filters.CharFilter(
        field_name="pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="pref_label",
    )
    parent = filters.UUIDFilter()

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        if not self.form.cleaned_data.get("parent"):
            qs = qs.filter(parent__isnull=True)
        return qs


class OrganizationViewSetQueryParamsSerializer(serializers.Serializer):
    expand_children = serializers.BooleanField(
        required=False,
        help_text=_("Show full child objects in list view instead of only identifiers."),
    )


class OrganizationViewSet(CommonReadOnlyModelViewSet):
    """List reference data organizations.

    To view children as objects instead of `id` values, use `?expand_children=true`.
    """

    filterset_class = OrganizationFilterSet
    serializer_class = OrganizationSerializer
    query_serializers = [{"class": OrganizationViewSetQueryParamsSerializer}]

    queryset = Organization.available_objects.filter(
        is_reference_data=True,
    ).prefetch_related("parent", "children", "children__children")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.query_params.get("expand_children"):
            ctx["expand_child_organizations"] = True
        return ctx
