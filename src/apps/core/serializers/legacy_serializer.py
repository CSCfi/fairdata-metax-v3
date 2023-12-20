from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.models import Dataset, LegacyDataset


class LegacyDatasetModelSerializer(CommonModelSerializer):
    def create(self, validated_data):
        identifier = validated_data["dataset_json"]["identifier"]
        if instance := LegacyDataset.objects.filter(id=identifier).first():
            return self.update(instance, validated_data)
        else:
            validated_data["id"] = identifier
            return super().create(validated_data)

    class Meta:
        model = LegacyDataset
        fields = (
            "id",
            "dataset_json",
            "contract_json",
            "files_json",
            "v2_dataset_compatibility_diff",
        )
        read_only_fields = ("id", "v2_dataset_compatibility_diff")
