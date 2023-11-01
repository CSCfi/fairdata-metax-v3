from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from apps.core.mixins import DatasetNestedViewSetMixin
from apps.core.models import Contract
from apps.core.serializers import ContractModelSerializer


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
class ContractViewSet(viewsets.ModelViewSet):
    serializer_class = ContractModelSerializer
    queryset = Contract.objects.all()
    filterset_class = ContractFilter
