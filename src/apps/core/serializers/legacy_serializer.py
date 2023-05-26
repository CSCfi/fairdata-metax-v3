from rest_framework import serializers

from apps.core.models import LegacyDataset


class LegacyDatasetModelSerializer(serializers.ModelSerializer):
    compatibility = serializers.SerializerMethodField()

    def get_compatibility(self, obj):
        return obj.check_compatibility()

    def create(self, validated_data):
        if LegacyDataset.objects.filter(
            dataset_json__identifier=validated_data["dataset_json"]["identifier"]
        ).exists():
            instance = LegacyDataset.objects.get(
                dataset_json__identifier=validated_data["dataset_json"]["identifier"]
            )
            return self.update(instance, validated_data)
        else:
            return super().create(validated_data)

    class Meta:
        model = LegacyDataset
        fields = ("id", "dataset_json", "contract_json", "files_json", "compatibility")
        read_only_fields = ("id",)
