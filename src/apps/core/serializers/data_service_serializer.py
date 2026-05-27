from rest_framework import serializers

from apps.common.serializers.fields import MultiLanguageField
from apps.common.serializers.serializers import CommonModelSerializer
from apps.core.models import DataService


class DataServiceModelSerializer(CommonModelSerializer):
    """Serialize DataService controlled list entry."""

    pref_label = MultiLanguageField(required=True)

    class Meta:
        model = DataService
        fields = ("id", "pref_label")
        read_only_fields = fields

