from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.models import Contract, Preservation


class ContractModelSerializer(serializers.ModelSerializer):
    """Model serializer for Contract"""

    class Meta:
        model = Contract
        fields = ("id", "title", "description", "quota", "valid_until")


class PreservationModelSerializer(CommonModelSerializer):
    """Model serializer for Preservation"""

    class Meta:
        model = Preservation
        fields = (
            "contract",
            "id",
            "state",
            "description",
            "reason_description",
        )

    def validate(self, attrs):
        preservation = None
        if self.instance:
            preservation = self.instance

        # If preservation state is other than NONE, dataset must have a
        # contract.
        if "state" in attrs or "contract" in attrs:
            state = Preservation.PreservationState.NONE  # Default
            if preservation:
                state = preservation.state  # Existing database value
            if "state" in attrs:
                state = attrs["state"]  # User-provided new value

            contract = None
            if preservation:
                contract = preservation.contract
            if "contract" in attrs:
                contract = attrs["contract"]

            if contract is None and state > -1:
                raise serializers.ValidationError(
                    {"contract": _(f"Dataset in preservation process must have a contract.")}
                )

        return super().validate(attrs)
