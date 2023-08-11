from rest_framework import serializers

from apps.core.models import Spatial
from apps.refdata import models as refdata


class SpatialModelSerializer(serializers.ModelSerializer):
    """Model Serializer for Spatial"""

    class Meta:
        model = Spatial
        fields = [
            "url",
            "pref_label",
            "in_scheme",
            "full_address",
            "geographic_name",
            "altitude_in_meters",
            "dataset",
        ]

    def create(self, validated_data):
        reference: refdata.Location
        url = validated_data.pop("url", None)

        if not url:
            raise serializers.ValidationError("Spatial needs url, got None")

        try:
            reference = refdata.Location.objects.get(url=url)
        except refdata.Location.DoesNotExist:
            raise serializers.ValidationError(f"Location not found {url}")

        return Spatial.objects.create(**validated_data, reference=reference)

    def update(self, instance, validated_data):
        url = validated_data.pop("url", instance.url)

        if url != instance.url:
            try:
                instance.reference = refdata.Location.objects.get(url=url)
            except refdata.Location.DoesNotExist:
                raise serializers.ValidationError(detail=f"Location not found {url}")

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        refdata_serializer = refdata.Location.get_serializer()
        refdata_serializer.omit_related = True
        serialized_ref = {}
        if getattr(instance, "reference", None):
            serialized_ref = refdata_serializer(instance.reference).data
        rep = super().to_representation(instance)
        return {**rep, **serialized_ref}
