import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.models.catalog_record.dataset import Dataset, UserRoleChoices

logger = logging.getLogger(__name__)


class DatasetUserRolesSerializer(serializers.ListSerializer):
    child = serializers.ChoiceField(choices=UserRoleChoices)

    def to_representation(self, instance: Dataset):
        data: list[str] = []
        if request := self.context["request"]:
            data = sorted(role.name for role in instance.get_user_roles(request.user))
        return super().to_representation(data)
