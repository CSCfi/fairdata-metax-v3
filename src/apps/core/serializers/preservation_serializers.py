from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.models import Dataset, Preservation


class PreservationDatasetSerializer(CommonModelSerializer):
    class Meta:
        model = Dataset
        fields = ("id", "persistent_identifier", "removed")


class PreservationModelSerializer(CommonModelSerializer):
    """Model serializer for Preservation"""

    dataset_version = PreservationDatasetSerializer(
        source="dataset_version.dataset", read_only=True
    )
    dataset_origin_version = PreservationDatasetSerializer(
        source="dataset_origin_version.dataset", read_only=True
    )

    class Meta:
        model = Preservation
        fields = (
            "id",
            "contract",
            "preservation_identifier",
            "state",
            "state_modified",
            "description",
            "reason_description",
            "dataset_version",
            "dataset_origin_version",
        )
        extra_kwargs = {
            "state_modified": {"read_only": True},
            "dataset_version": {"read_only": True},
            "dataset_origin_version": {"read_only": True},
        }

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

    def create(self, validated_data):
        if (
            "state" in validated_data
            and validated_data["state"] >= Preservation.PreservationState.INITIALIZED
        ):
            validated_data["state_modified"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "state" in validated_data and validated_data["state"] != instance.state:
            validated_data["state_modified"] = timezone.now()
        return super().update(instance, validated_data)
