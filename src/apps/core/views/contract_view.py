from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.views import CommonModelViewSet
from apps.core.models import Contract
from apps.core.permissions import ContractAccessPolicy
from apps.core.serializers import ContractModelSerializer
from apps.core.serializers.contract_serializers import LegacyContractSerializer


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

    @swagger_auto_schema(
        request_body=LegacyContractSerializer(),
        responses={200: ContractModelSerializer(), 201: ContractModelSerializer},
    )
    @action(detail=False, methods=["post"], url_path="from-legacy")
    def from_legacy(self, request):
        contract, created = Contract.create_or_update_from_legacy(request.data)
        rep = ContractModelSerializer(instance=contract).data
        return Response(rep, status=201 if created else 200)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        serializer.instance.signal_sync()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        serializer.instance.signal_sync()

    def perform_destroy(self, instance: Contract):
        super().perform_destroy(instance)  # soft delete
        instance.signal_sync()
