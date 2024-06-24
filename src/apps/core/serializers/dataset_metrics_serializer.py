from rest_framework import serializers

from apps.core.models import DatasetMetrics


class DatasetMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetMetrics
        fields = ["modified", *DatasetMetrics.metrics_fields]


class DatasetMetricsQueryParamsSerializer(serializers.Serializer):
    include_metrics = serializers.BooleanField(
        help_text="Include dataset view and download metrics in the response.",
        required=False,
    )
