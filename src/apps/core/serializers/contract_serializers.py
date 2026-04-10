import logging

from typing import Optional

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
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.contract import ContractContact, ContractService, ContractSensitivityRationale
from apps.core.models.concepts import SensitivityRationale
from apps.users.models import MetaxUser

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


class ContractSensitivityRationaleSerializer(CommonModelSerializer):
    rationale = SensitivityRationale.get_serializer_field(required=True)

    class Meta:
        list_serializer_class = CommonListSerializer
        model = ContractSensitivityRationale
        fields = ("id", "rationale", "expiration_date")


class ContractDataSensitivitySerializer(CommonNestedModelSerializer):
    """Contract data sensitivity serializer."""

    rationales = ContractSensitivityRationaleSerializer(many=True, min_length=0)


    class Meta:
        model = Contract
        fields = ("is_sensitive", "rationales")


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
    data_sensitivity = ContractDataSensitivitySerializer(
        source="*", required=False
    )

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
            "data_sensitivity",
            "removed",
        )
        extra_kwargs = {
            "removed": {"read_only": True},
        }

    def has_permission_to_view_sensitivity(self, user: MetaxUser) -> bool:
        """
        Determine if user has permission to view data sensitivity information
        """
        if user.is_superuser:
            return True
        if not user.is_authenticated:
            return False

        return user.is_pas_service

    def to_representation(self, instance: Contract):
        result = super().to_representation(instance)

        include_hidden_fields = self.context.get("include_hidden_fields")

        # If 'include_hidden_fields' is not provided explicitly, check
        # user permissions to determine field visibility.
        if include_hidden_fields is None:
            user = self.context["request"].user

            # Hide 'data_sensitivity' field for non-PAS users
            include_hidden_fields = self.has_permission_to_view_sensitivity(user)

        if not include_hidden_fields:
            result.pop("data_sensitivity", None)

        return result

    @classmethod
    def validate_new_data_sensitivity(
        cls,
        contract: Optional["Contract"],
        new_is_sensitive: Optional[bool] = None,
        new_rationales: Optional[list[ContractSensitivityRationale]] = None,
    ):
        """
        Validate that new contract and any linked datasets remain valid
        after update:

        * contract cannot be made non-sensitive if any datasets are sensitive
        * rationales cannot be removed if any datasets still use them
        """
        if contract:
            # For values not being updated, use their existing values
            if new_is_sensitive is None:
                new_is_sensitive = contract.is_sensitive
            if new_rationales is None:
                new_rationales = contract.rationales

        # If 'is_sensitive' is being set to False, query for datasets that
        # are still sensitive
        if new_is_sensitive is False:
            dataset_ids = [
                str(dataset.id) for dataset
                in Dataset.objects.filter(
                    preservation__contract=contract.id, is_sensitive=True
                ).only("id")
            ]
            if dataset_ids:
                raise serializers.ValidationError({
                    "is_sensitive": (
                        f"Following datasets are still sensitive: {', '.join(dataset_ids)}"
                    )
                })

        # If rationales are changed, retrieve any that are being removed
        # and query for datasets still using them
        if new_rationales is not None:
            try:
                # Cast query set to list
                new_rationales = list(new_rationales.all())
            except AttributeError:
                pass

            new_rationale_urls = {
                new_rationale["rationale"].url for new_rationale in new_rationales
            }
            old_rationale_urls = {
                old_rationale.rationale.url for old_rationale
                in contract.rationales.prefetch_related("rationale")
            } if contract else set()

            removed_rationale_urls = old_rationale_urls - new_rationale_urls

            if removed_rationale_urls:
                dataset_ids = [
                    str(dataset.id) for dataset
                    in Dataset.objects.filter(
                        preservation__contract=contract.id,
                        is_sensitive=True, rationales__rationale__url__in=removed_rationale_urls
                    ).only("id")
                ]

                if dataset_ids:
                    raise serializers.ValidationError({
                        "rationales": (
                            f"Following datasets still use rationales that are "
                            f"being removed: {', '.join(dataset_ids)}"
                        )
                    })

    def update(self, instance, validated_data):
        if "id" in validated_data and validated_data["id"] != instance.id:
            raise serializers.ValidationError(
                {"id": "Value cannot be changed for an existing contract."}
            )

        if "is_sensitive" in validated_data or "rationales" in validated_data:
            self.validate_new_data_sensitivity(
                contract=instance,
                new_is_sensitive=validated_data.get("is_sensitive"),
                new_rationales=validated_data.get("rationales")
            )

        return super().update(instance, validated_data)

    def create(self, validated_data):
        self.validate_new_data_sensitivity(
            contract=None,
            new_is_sensitive=validated_data.get("is_sensitive"),
            new_rationales=validated_data.get("rationales")
        )

        return super().create(validated_data=validated_data)


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
