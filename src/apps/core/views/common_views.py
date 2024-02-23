import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.common.views import CommonModelViewSet
from apps.core.models import AccessRights
from apps.core.models.data_catalog import DatasetPublisher
from apps.core.serializers import DatasetPublisherModelSerializer

logger = logging.getLogger(__name__)


class DatasetPublisherFilter(filters.FilterSet):
    class Meta:
        model = DatasetPublisher
        fields = ("name", "homepage__url", "homepage__title")

    homepage__title = filters.CharFilter(
        field_name="homepage__title__values",
        max_length=255,
        lookup_expr="icontains",
        label="homepage__title",
    )
    homepage__url = filters.CharFilter(max_length=512, lookup_expr="icontains", label="url")
    name = filters.CharFilter(
        field_name="name__values",
        max_length=255,
        lookup_expr="icontains",
        label="name",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("name__values", "name"),
            ("homepage__url", "url"),
            ("homepage__title__values", "homepage__title"),
        )
    )


class AccessRightsFilter(filters.FilterSet):
    class Meta:
        model = AccessRights
        fields = (
            "description",
            "access_type__url",
            "access_type__pref_label",
            "license__url",
            "license__pref_label",
        )

    description = filters.CharFilter(
        field_name="description__values",
        max_length=255,
        lookup_expr="icontains",
        label="description",
    )

    access_type__url = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="access_type__url",
    )

    access_type__pref_label = filters.CharFilter(
        field_name="access_type__pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="access_type__pref_label",
    )

    license__url = filters.CharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="license__url",
    )

    license__pref_label = filters.CharFilter(
        field_name="license__pref_label__values",
        max_length=255,
        lookup_expr="icontains",
        label="license__pref_label",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("description__values", "description"),
            ("access_type__url", "access_type__url"),
            ("access_type__pref_label__values", "access_type__pref_label"),
            ("license__url", "license__url"),
            ("license__pref_label__values", "license__pref_label"),
        )
    )


class DefaultValueOrdering(filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        if "default" in kwargs:
            self.default = kwargs["default"]
            del kwargs["default"]
        super().__init__(**kwargs)

    def filter(self, qs, value):
        if self.default and value is None or len(value) == 0:
            return qs.order_by(self.get_ordering_value(self.default))
        return super().filter(qs, value)
