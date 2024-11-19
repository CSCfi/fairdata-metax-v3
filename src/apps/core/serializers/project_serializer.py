from rest_framework import validators

from apps.common.serializers import CommonListSerializer, CommonNestedModelSerializer
from apps.core.models import DatasetProject, Funder, FunderType, Funding
from apps.core.serializers.dataset_actor_serializers.organization_serializer import (
    DatasetOrganizationSerializer,
)
from apps.common.serializers.validators import AnyOf


class FunderSerializer(CommonNestedModelSerializer):
    organization = DatasetOrganizationSerializer(many=False, required=False, allow_null=True)
    funder_type = FunderType.get_serializer_field(many=False, required=False, allow_null=True)

    class Meta:
        model = Funder
        fields = (
            "organization",
            "funder_type",
        )
        validators = [AnyOf(["organization", "funder_type"])]


class FundingModelSerializer(CommonNestedModelSerializer):
    funder = FunderSerializer(required=False, allow_null=True)

    class Meta:
        model = Funding
        fields = (
            "funder",
            "funding_identifier",
        )


class ProjectModelSerializer(CommonNestedModelSerializer):
    participating_organizations = DatasetOrganizationSerializer(
        many=True, required=True, allow_null=False, min_length=1
    )
    funding = FundingModelSerializer(many=True, required=False, allow_null=True)

    def to_internal_value(self, data):
        # The participating_organizations field is optional when migrating V2 datasets
        org_field = self.fields["participating_organizations"]
        if self.context.get("migrating"):
            org_field.required = False
            org_field.allow_null = True
            org_field.min_length = 0
        else:
            org_field.required = True
            org_field.allow_null = False
            org_field.min_length = 1
        return super().to_internal_value(data)

    class Meta:
        model = DatasetProject
        fields = (
            "id",
            "title",
            "project_identifier",
            "participating_organizations",
            "funding",
        )
        list_serializer_class = CommonListSerializer
