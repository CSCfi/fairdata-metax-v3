import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404

from apps.common.views import CommonModelViewSet
from apps.core.models import Dataset
from apps.core.permissions import DatasetAccessPolicy, DatasetNestedAccessPolicy
from apps.core.serializers import (
    AccessRightsModelSerializer,
    DatasetActorSerializer,
    ProvenanceModelSerializer,
)

logger = logging.getLogger(__name__)


class DatasetNestedViewSet(CommonModelViewSet):
    access_policy = DatasetNestedAccessPolicy

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return self.serializer_class.Meta.model.available_objects.none()

        dataset = self.get_dataset_instance()
        return self.serializer_class.Meta.model.available_objects.filter(dataset=dataset)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        self.get_dataset_instance().signal_update()
        return resp

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        self.get_dataset_instance().signal_update()
        return resp

    def perform_create(self, serializer):
        dataset = self.get_dataset_instance()
        return serializer.save(dataset_id=dataset.id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "swagger_fake_view", None):
            # kwargs are not available in swagger inspection
            return context
        context["dataset"] = self.get_dataset_instance()
        return context

    def get_dataset_instance(self) -> Dataset:
        dataset_qs = Dataset.available_objects.filter(id=self.kwargs["dataset_pk"])
        dataset_qs = DatasetAccessPolicy().scope_queryset(self.request, dataset_qs)
        return get_object_or_404(dataset_qs)


class DatasetNestedOneToOneView(DatasetNestedViewSet):
    http_method_names = ["get", "put", "patch", "delete", "options"]

    def __init__(self, *args, **kwargs):
        if not getattr(self, "dataset_field_name", None):
            raise ValueError(f"Missing dataset_field_name from {self.__class__.__name__}")
        super().__init__(*args, **kwargs)

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        obj = None
        if not kwargs.get("patch"):
            # Allow creating new object when in PUT mode
            queryset = self.get_queryset()
            (
                obj,
                created,
            ) = queryset.get_or_create()  # Create initial object if it does not exist yet
            if created:
                from apps.core.models.catalog_record.dataset import Dataset

                # Assign created object to Dataset.<dataset_field_name>
                Dataset.objects.filter(id=self.kwargs["dataset_pk"]).update(
                    **{self.dataset_field_name: obj}
                )
        return super().update(request, *args, **kwargs)


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


class ProvenanceViewSet(DatasetNestedViewSet):
    serializer_class = ProvenanceModelSerializer
    filterset_class = ProvenanceFilter


@swagger_auto_schema(operation_description="DatasetActor viewset")
class DatasetActorViewSet(DatasetNestedViewSet):
    serializer_class = DatasetActorSerializer


class AccessRightsViewSet(DatasetNestedOneToOneView):
    serializer_class = AccessRightsModelSerializer
    dataset_field_name = "access_rights"
