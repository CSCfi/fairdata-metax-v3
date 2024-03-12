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
    url = filters.CharFilter()
    deprecated = filters.BooleanFilter(lookup_expr="isnull", exclude=True)
    include_suborganizations = filters.BooleanFilter(
        method="filter_include_suborganizations",
        label=_("Also include suborganizations in the list."),
    )

    def filter_include_suborganizations(self, queryset, name, value):
        """Hide suborganizations in list unless filter is enabled or parent is set."""
        parent = self.form.cleaned_data.get("parent")
        if not value and not parent:
            return queryset.filter(parent__isnull=True)  # Show only top-level orgs
        return queryset

    def filter_queryset(self, queryset):
        # Hide deprecated organizations by default
        if self.form.cleaned_data["deprecated"] is None:
            self.form.cleaned_data["deprecated"] = False
        # Hide suborganizations in the top list level by default
        if self.form.cleaned_data["include_suborganizations"] is None:
            self.form.cleaned_data["include_suborganizations"] = False
        return super().filter_queryset(queryset)


class OrganizationViewSetQueryParamsSerializer(serializers.Serializer):
    expand_children = serializers.BooleanField(
        default=False,
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
