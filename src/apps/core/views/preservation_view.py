from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.common.views import CommonModelViewSet
from apps.core.mixins import DatasetNestedViewSetMixin
from apps.core.models import Contract, Dataset, Preservation
from apps.core.permissions import ContractAccessPolicy
from apps.core.serializers import ContractModelSerializer, PreservationModelSerializer


class ContractFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title__values",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )
    id = filters.CharFilter(max_length=255, lookup_expr="icontains")


@method_decorator(
    name="list", decorator=swagger_auto_schema(operation_description="List Contracts")
)
class ContractViewSet(CommonModelViewSet):
    serializer_class = ContractModelSerializer
    queryset = Contract.objects.all()
    filterset_class = ContractFilter
    access_policy = ContractAccessPolicy


@method_decorator(
    name="retrieve", decorator=swagger_auto_schema(operation_description="View Preservation")
)
class PreservationViewSet(DatasetNestedViewSetMixin):
    serializer_class = PreservationModelSerializer

    lookup_field = "pk"

    http_method_names = ["get", "put", "patch", "options"]

    def get_queryset(self):
        dataset = Dataset.objects.only("preservation_id").get(pk=self.kwargs["dataset_pk"])
        return Preservation.objects.filter(id=dataset.preservation_id)

    def get_object(self):
        queryset = self.get_queryset()
        preservation, created = queryset.get_or_create()

        if created:
            Dataset.objects.filter(id=self.kwargs["dataset_pk"]).update(
                preservation_id=preservation.id
            )

        return preservation
