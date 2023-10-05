import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.common.views import CommonModelViewSet, StandardResultsSetPagination
from apps.core.models import AccessRights
from apps.core.models.catalog_record import DatasetActor, MetadataProvider
from apps.core.models.data_catalog import DatasetPublisher
from apps.core.serializers import (
    DatasetActorModelSerializer,
    DatasetPublisherModelSerializer,
    MetadataProviderModelSerializer,
)

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
        field_name="name__values", max_length=255, lookup_expr="icontains", label="name"
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


@swagger_auto_schema(operation_description="Publisher viewset")
class PublisherViewSet(CommonModelViewSet):
    serializer_class = DatasetPublisherModelSerializer
    queryset = DatasetPublisher.objects.all()
    filterset_class = DatasetPublisherFilter
    http_method_names = ["get", "post", "put", "delete"]


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


@swagger_auto_schema(operation_description="DatasetActor viewset")
class DatasetActorViewSet(CommonModelViewSet):
    serializer_class = DatasetActorModelSerializer
    filter_backends = (filters.DjangoFilterBackend,)

    # filterset_class = DatasetActorFilter
    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return DatasetActor.available_objects.none()
        return DatasetActor.available_objects.filter(dataset=self.kwargs["dataset_pk"])

    def perform_create(self, serializer):
        return serializer.save(dataset_id=self.kwargs["dataset_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dataset_pk"] = self.kwargs.get("dataset_pk")
        return context


class MetadataProviderFilter(filters.FilterSet):
    organization = filters.CharFilter(
        field_name="organization",
        max_length=512,
        lookup_expr="icontains",
        label="organization",
    )

    user__first_name = filters.CharFilter(
        max_length=150,
        lookup_expr="icontains",
        label="user__first_name",
    )

    user__last_name = filters.CharFilter(
        max_length=150,
        lookup_expr="icontains",
        label="user__last_name",
    )

    user__email = filters.CharFilter(
        max_length=254,
        lookup_expr="icontains",
        label="user__email",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("organization", "organization"),
            ("user__first_name", "user__first_name"),
            ("user__last_name", "user__last_name"),
            ("user__email", "user__email"),
        )
    )


class MetadataProviderViewSet(CommonModelViewSet):
    serializer_class = MetadataProviderModelSerializer
    queryset = MetadataProvider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = MetadataProviderFilter
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "put", "delete"]


class DatasetFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )
