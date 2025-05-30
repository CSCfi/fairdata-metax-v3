import logging

from django.db import models
from rest_framework import serializers, validators

from apps.common.helpers import single_translation
from apps.common.serializers.fields import LaxIntegerField, NoopField
from apps.common.serializers.serializers import (
    CommonListSerializer,
    CommonModelSerializer,
    CommonNestedModelSerializer,
)
from apps.core.models import Contract
from apps.core.models.contract import ContractContact, ContractService

logger = logging.getLogger(__name__)


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

    id = serializers.CharField(
        max_length=64,
        validators=[
            validators.UniqueValidator(
                queryset=Contract.objects.all(), message="Contract with this value already exists."
            )
        ],
    )

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
            "title",
            "description",
            "quota",
            "created",
            "modified",
            "organization",
            "validity",
            "contact",
            "related_service",
            "removed",
        )
        extra_kwargs = {
            "removed": {"read_only": True},
        }

    def update(self, instance, validated_data):
        if "id" in validated_data and validated_data["id"] != instance.id:
            raise serializers.ValidationError(
                {"id": "Value cannot be changed for an existing contract."}
            )
        return super().update(instance, validated_data)


class LegacyContractJSONSerializer(ContractModelSerializer):
    """Serializer for legacy contract_json.

    Used as part of LegacyContractSerializer.
    """

    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    identifier = serializers.CharField(source="id")
    quota = LaxIntegerField()  # Legacy Metax allows float values in quota

    def to_internal_value(self, data):
        # From legacy to V3 dict
        data = super().to_internal_value(data)
        data["title"] = {"und": data["title"]}
        if desc := data.get("description"):
            data["description"] = {"und": desc}
        else:
            data["description"] = None
        if quota := data.get("quota"):
            # Some legacy test data has quota larger than postgres MAX_BIGINT
            if quota > models.BigIntegerField.MAX_BIGINT:
                data["quota"] = models.BigIntegerField.MAX_BIGINT
                logger.warning(f"Contract quota {quota} too large, setting to MAX_BIGINT.")
        return data

    def to_representation(self, instance):
        # From V3 instance to legacy
        rep = super().to_representation(instance)
        rep["title"] = single_translation(instance.title)
        if instance.description:
            rep["description"] = single_translation(instance.description)
        return rep

    class Meta:
        model = Contract
        fields = (
            *(f for f in ContractModelSerializer.Meta.fields if f != "id"),
            "identifier",
        )


class LegacyContractSerializer(ContractModelSerializer):
    """Serializer for legacy contract to V3 conversion.

    Deserializers legacy contract into V3 contract. Because
    most legacy data is in contact_json, this is essentially
    a wrapper for LegacyContractJSONSerializer.
    """

    id = serializers.IntegerField(source="legacy_id")
    date_created = serializers.DateTimeField(source="record_created")
    date_modified = serializers.DateTimeField(source="record_modified")
    date_removed = serializers.DateTimeField(required=False, allow_null=True)
    removed = serializers.BooleanField(default=False)
    service_created = NoopField()
    service_modified = NoopField()
    user_created = NoopField()
    user_modified = NoopField()

    # Use source="*" so the nested serializer gets the entire Contract object
    # and operates on the same internal value as this serializer.
    contract_json = LegacyContractJSONSerializer(source="*")

    class Meta:
        model = Contract
        fields = [
            "id",
            "date_created",
            "date_modified",
            "service_created",
            "service_modified",
            "user_created",
            "user_modified",
            "contract_json",
            "date_removed",
            "removed",
        ]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # Combine date_removed and removed into one value
        date_removed = data.pop("date_removed", None)
        if data.get("removed"):
            data["removed"] = date_removed
        else:
            data["removed"] = None

        return data

    @property
    def _readable_fields(self):
        for field in super()._readable_fields:
            # date_removed is handled manually in to_representation
            if field.field_name != "date_removed":
                yield field

    def to_representation(self, instance: Contract):
        rep = super().to_representation(instance)
        rep["date_removed"] = instance.removed
        rep["id"] = instance.legacy_id
        return rep

    def save(self):
        data = self._validated_data

        # Use LegacyContractJSONSerializer for saving to get nested fields saved correctly
        serializer = self.fields["contract_json"]
        serializer._validated_data = data
        serializer._errors = []
        serializer.instance = self.instance
        self.instance = serializer.save()
        return self.instance
