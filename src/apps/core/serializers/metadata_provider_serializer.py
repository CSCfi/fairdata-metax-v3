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
from apps.users.models import AdminOrganization
from apps.core.management.initial_data.admin_org_map import admin_org_map

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
        fields = ("id", "user", "organization", "admin_organization")

    def to_internal_value(self, data):
        """Remove admin_organization from validated_data if it's not in input data."""
        internal_value = super().to_internal_value(data)
        if "admin_organization" not in data:
            internal_value.pop("admin_organization", None)
        return internal_value

    def is_custom_value_allowed(self):
        """End-users should not be allowed to use custom values."""
        if self.context.get("migrating"):
            return True
        request = self.context["request"]
        return DatasetAccessPolicy().query_object_permission(  # note that instance may be null
            user=request.user, object=self.instance, action="<op:custom_metadata_owner>"
        )

    def get_user_default_data(self):
        """Return default user and organization values for user."""
        user = self.context["request"].user
        return {
            "user": user.username,
            "organization": user.organization or user.username,
        }

    def check_user_data(self, data):
        """Validate user-provided data."""
        if self.is_custom_value_allowed():
            return  # Services can use any values for username and organization

        # End users are not allowed to change the existing/default values for user and organization
        if self.instance:
            expected_values = {
                "user": self.instance.user.username,
                "organization": self.instance.organization,
            }
        else:
            expected_values = self.get_user_default_data()

        errors = {}
        if data["user"] != expected_values["user"]:
            errors["user"] = f"Not allowed to change value. Expected '{expected_values['user']}'."
        if data["organization"] != expected_values["organization"]:
            errors["organization"] = (
                f"Not allowed to change value. Expected '{expected_values['organization']}'."
            )
        if errors:
            raise serializers.ValidationError(errors)

    def save(self, **kwargs):
        """Save with support for custom values.

        Call save with an empty dict as self._validated_data
        to use values from request user."""
        data = self._validated_data

        if data:
            self.check_user_data(data)
        else:
            data = self.get_user_default_data()  # Use values from request user as defaults

        return super().save(**data)

    def validate_admin_organization(self, value):
        if not (value is None or AdminOrganization.objects.filter(id=value).exists()):
            raise serializers.ValidationError(f"Value is not allowed: {value}")
        return value

    # todo: map these to AdminOrganization objects using other_identifier
    def get_admin_organization_for_organization(self, organization: str) -> str | None:
        if organization in admin_org_map:
            return admin_org_map[organization]

        if admin_organization := AdminOrganization.objects.filter(id=organization).first():
            return admin_organization.id

        return None

    def get_or_create_provider(self, validated_data):
        """Reuse existing metadata provider when possible."""
        user, created = get_user_model().objects.get_or_create(username=validated_data["user"])
        organization = validated_data["organization"]

        if "admin_organization" in validated_data:
            admin_organization = validated_data["admin_organization"]
        elif self.instance:
            admin_organization = self.instance.admin_organization
        else:
            admin_organization = self.get_admin_organization_for_organization(organization)

        if admin_organization:
            provider = MetadataProvider.objects.filter(
                user=user,
                organization=organization,
                admin_organization=admin_organization,
            ).first()
        else:
            provider = MetadataProvider.objects.filter(
                user=user, organization=organization, admin_organization__isnull=True
            ).first()
        if provider:
            return provider

        return MetadataProvider.objects.create(
            user=user,
            organization=organization,
            admin_organization=admin_organization,
        )

    def create(self, validated_data):
        return self.get_or_create_provider(validated_data)

    def update(self, instance, validated_data):
        return self.get_or_create_provider(validated_data)
