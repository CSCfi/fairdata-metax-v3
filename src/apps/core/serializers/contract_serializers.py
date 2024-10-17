from rest_framework import serializers

from apps.common.serializers.serializers import (
    CommonListSerializer,
    CommonModelSerializer,
    CommonNestedModelSerializer,
)
from apps.core.models import Contract
from apps.core.models.contract import ContractContact, ContractService


class ContractContactSerializer(CommonModelSerializer):
    """Model serializer for ContractContact"""

    email = serializers.EmailField()

    class Meta:
        list_serializer_class = CommonListSerializer
        model = ContractContact
        fields = ("name", "email", "phone")


class ContractServiceSerializer(CommonModelSerializer):
    """Model serializer for ContractService"""

    class Meta:
        list_serializer_class = CommonListSerializer
        model = ContractService
        fields = ("identifier", "name")


class ContractOrganizationSerializer(CommonModelSerializer):
    """Contract organization serializer. Should be used with source="*"."""

    class Meta:
        model = Contract
        fields = ("name", "organization_identifier")
        extra_kwargs = {"name": {"source": "organization_name"}}


class ContractValiditySerializer(CommonModelSerializer):
    """Contract validity serializer. Should be used with source="*"."""

    class Meta:
        model = Contract
        fields = ("start_date", "end_date")
        extra_kwargs = {
            "start_date": {"source": "validity_start_date"},
            "end_date": {"source": "validity_end_date"},
        }


class ContractModelSerializer(CommonNestedModelSerializer):
    """Model serializer for Contract"""

    # One-to-one objects included in the contract model
    organization = ContractOrganizationSerializer(source="*")
    validity = ContractValiditySerializer(source="*")

    # To-many relations
    contact = ContractContactSerializer(many=True, min_length=1)
    related_service = ContractServiceSerializer(many=True, min_length=1)

    class Meta:
        model = Contract
        fields = (
            "id",
            "contract_identifier",
            "title",
            "description",
            "quota",
            "created",
            "modified",
            "organization",
            "validity",
            "contact",
            "related_service",
        )
