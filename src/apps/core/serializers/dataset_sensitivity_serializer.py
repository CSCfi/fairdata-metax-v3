from apps.common.serializers import (
    CommonListSerializer,
    CommonModelSerializer,
    CommonNestedModelSerializer
)
from apps.core.models.catalog_record.data_sensitivity import DatasetSensitivityRationale
from apps.core.models import Dataset

from apps.core.models.concepts import SensitivityRationale


class DatasetSensitivityRationaleSerializer(CommonModelSerializer):
    rationale = SensitivityRationale.get_serializer_field(required=True)

    class Meta:
        list_serializer_class = CommonListSerializer
        model = DatasetSensitivityRationale
        fields = ("id", "rationale", "expiration_date")


class DatasetDataSensitivitySerializer(CommonNestedModelSerializer):
    """Dataset data sensitivity serializer"""

    rationales = DatasetSensitivityRationaleSerializer(many=True, min_length=0)

    class Meta:
        model = Dataset
        fields = ("is_sensitive", "rationales")

