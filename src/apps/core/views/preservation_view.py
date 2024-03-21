from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema

from apps.common.views import CommonModelViewSet
from apps.core.models import Contract
from apps.core.permissions import ContractAccessPolicy
from apps.core.serializers import ContractModelSerializer, PreservationModelSerializer
from apps.core.views.nested_views import DatasetNestedOneToOneView


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
class PreservationViewSet(DatasetNestedOneToOneView):
    serializer_class = PreservationModelSerializer
    dataset_field_name = "preservation"
