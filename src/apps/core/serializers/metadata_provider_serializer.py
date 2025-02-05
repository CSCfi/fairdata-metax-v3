import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.serializers import AbstractDatasetModelSerializer
from apps.common.serializers.fields import PrivateUsernameValue
from apps.common.serializers.serializers import StrictSerializer
from apps.core.models import MetadataProvider
from apps.core.permissions import DatasetAccessPolicy
from apps.users.models import MetaxUser

logger = logging.getLogger(__name__)


class UsernameField(serializers.CharField):
    """CharField that returns non-JSON-serializable username.

    To allow JSON serialization, replace the PrivateUsernameValue
    object with its .value.
    """

    def to_representation(self, value):
        if isinstance(value, MetaxUser):
            return PrivateUsernameValue(value.username)
        return PrivateUsernameValue(value)


class MetadataProviderModelSerializer(AbstractDatasetModelSerializer):
    """Metadata provider handling logic.

    Creates or retrieves MetadataProvider object based on request data.
    Does not alter existing objects.

    Call `save()` with `serializer._validated_data={}` to use default provider. Defaults are:
    - If instance exists, use provider values from instance
    - If instance does not exist, use provider values from request user
    """

    user = UsernameField()

    class Meta:
        model = MetadataProvider
        fields = ("id", "user", "organization")

    def is_custom_value_allowed(self):
        """End-users should not be allowed to use custom values."""
        if self.context.get("migrating"):
            return True
        request = self.context["request"]
        return DatasetAccessPolicy().query_object_permission(  # note that instance may be null
            user=request.user, object=self.instance, action="<op:custom_metadata_owner>"
        )

    def save(self, **kwargs):
        """Save with support for custom values.

        Call save with an empty dict as self._validated_data
        to use request user."""
        data = self._validated_data

        # Default to existing values or values from authenticated user
        if data and self.is_custom_value_allowed():
            ctx_data = data
        elif self.instance:
            ctx_data = {
                "user": self.instance.user.username,
                "organization": self.instance.organization,
            }
        else:
            user = self.context["request"].user
            ctx_data = {
                "user": user.username,
                "organization": user.organization or user.username,
            }

        if not data:
            # Data is empty, use values from request user
            data = ctx_data
        else:
            # Data has values but they should match the request user
            errors = {}
            if data["user"] != ctx_data["user"]:
                errors["user"] = _("Not allowed to change value. Expected '{}'.").format(
                    ctx_data["user"]
                )
            if data["organization"] != ctx_data["organization"]:
                errors["organization"] = _(
                    _("Not allowed to change value. Expected '{}'.")
                ).format(ctx_data["organization"])
            if errors:
                raise serializers.ValidationError(errors)
        return super().save(**data)

    def get_or_create_provider(self, validated_data):
        """Reuse existing metadata provider when possible."""
        user, created = get_user_model().objects.get_or_create(username=validated_data["user"])
        organization = validated_data["organization"]
        provider = MetadataProvider.objects.filter(user=user, organization=organization).first()
        if provider:
            return provider
        return MetadataProvider.objects.create(user=user, organization=organization)

    def create(self, validated_data):
        return self.get_or_create_provider(validated_data)

    def update(self, instance, validated_data):
        return self.get_or_create_provider(validated_data)
