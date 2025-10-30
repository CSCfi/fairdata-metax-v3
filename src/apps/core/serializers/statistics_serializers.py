from rest_framework import serializers
from apps.core.models import OrganizationStatistics, ProjectStatistics


class OrganizationStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationStatistics
        fields = [
            "organization",
            "count_total",
            "count_ida",
            "count_pas",
            "count_att",
            "count_other",
            "byte_size_total",
            "byte_size_ida",
            "byte_size_pas",
        ]
        read_only_fields = ["__all__"]


class ProjectStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStatistics
        fields = [
            "project_identifier",
            "ida_count",
            "ida_byte_size",
            "ida_published_datasets",
            "pas_count",
            "pas_byte_size",
            "pas_published_datasets",
        ]
        read_only_fields = ["__all__"]
