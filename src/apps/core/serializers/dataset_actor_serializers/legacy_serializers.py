import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.actors.models import Organization
from apps.core.serializers.dataset_actor_serializers.actor_serializer import (
    DatasetActorProvenanceSerializer,
    DatasetActorSerializer,
)
from apps.core.serializers.dataset_actor_serializers.member_serializer import DatasetMemberContext
from apps.core.serializers.dataset_actor_serializers.organization_serializer import (
    DatasetOrganizationSerializer,
)

logger = logging.getLogger(__name__)


class LegacyDatasetOrganizationSerializer(DatasetOrganizationSerializer):
    """Dataset organization serializer for migrating legacy data.

    Allows creating a new reference data organization when one does not already exist.
    The organization is marked as deprecated and will not be displayed in organization
    list.
    """

    def handle_missing_reference_data(self, attrs: dict, comparison_data: dict):
        url = attrs["url"]
        if not url.startswith(settings.ORGANIZATION_BASE_URI):
            logger.warn(
                f"Legacy organization identifier not from reference data, not creating: {url}"
            )
            return super().handle_missing_reference_data(attrs, comparison_data)

        if parent := attrs.get("parent"):
            parent_url = parent.get("url") or parent.get("external_identifier") or ""
            if not parent_url.startswith(settings.ORGANIZATION_SCHEME):
                raise serializers.ValidationError(
                    {
                        "parent": f"Reference organization {url} cannot be child of non-reference organization {parent_url}"
                    }
                )

        # Add field values needed by legacy reference data orgs
        attrs["id"] = f"#{attrs['url']}"
        attrs["is_reference_data"] = True
        attrs["in_scheme"] = settings.ORGANIZATION_SCHEME
        attrs["deprecated"] = timezone.now()
        return attrs


class LegacyDatasetActorSerializer(DatasetActorSerializer):
    """Dataset actor serializer for migrating legacy data."""

    organization = LegacyDatasetOrganizationSerializer(required=False, allow_null=True)


class LegacyDatasetActorProvenanceSerializer(DatasetActorProvenanceSerializer):
    """Dataset provenance actor serializer for migrating legacy data."""

    organization = LegacyDatasetOrganizationSerializer(required=False, allow_null=True)
