from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models import Contract
from apps.common.serializers.serializers import CommonModelSerializer


class ContractModelSerializer(serializers.ModelSerializer):
    """Model serializer for Contract"""

    class Meta:
        model = Contract
        fields = ("id", "title", "description", "quota", "valid_until")
