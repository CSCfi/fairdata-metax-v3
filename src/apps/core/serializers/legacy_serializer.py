from rest_framework import serializers

from apps.core.models import LegacyDataset


class LegacyDatasetModelSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        if instance := LegacyDataset.objects.filter(
            dataset_json__identifier=validated_data["dataset_json"]["identifier"]
        ).first():
            return self.update(instance, validated_data)
        else:
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
