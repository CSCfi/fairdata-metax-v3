from rest_framework import serializers

from apps.common.serializers.fields import WKTField
from apps.common.serializers.serializers import CommonListSerializer, CommonModelSerializer
from apps.common.serializers.validators import AnyOf
from apps.core.models import Spatial, concepts


class SpatialModelSerializer(CommonModelSerializer):
    """Model Serializer for Spatial"""

    reference = concepts.Location.get_serializer_field(required=False, allow_null=True)
    custom_wkt = serializers.ListField(child=WKTField(), required=False, allow_null=True)

    class Meta:
        model = Spatial
        list_serializer_class = CommonListSerializer
        fields = [
            "full_address",
            "geographic_name",
            "altitude_in_meters",
            "reference",
            "custom_wkt",
        ]
        list_serializer_class = CommonListSerializer
        validators = [
            AnyOf(
                [
                    "full_address",
                    "geographic_name",
                    "altitude_in_meters",
                    "reference",
                    "custom_wkt",
                ]
            )
        ]
