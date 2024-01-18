from rest_framework import serializers

from apps.actors.serializers import CompactOrganizationSerializer
from apps.core.models import DatasetProject, Funding, Funder, FunderType
from apps.common.serializers import CommonListSerializer, CommonNestedModelSerializer


class FunderSerializer(CommonNestedModelSerializer):
    organization = CompactOrganizationSerializer(many=False, required=True)
    funder_type = FunderType.get_serializer_field(many=False, required=False)

    class Meta:
        model = Funder
        fields = (
            "organization",
            "funder_type",
        )


class FundingModelSerializer(CommonNestedModelSerializer):
    funder = FunderSerializer(many=False, required=True)

    class Meta:
        model = Funding
        fields = (
            "funder",
            "funding_identifier",
        )


class ProjectModelSerializer(CommonNestedModelSerializer):
    participating_organizations = CompactOrganizationSerializer(many=True, required=False)
    funding = FundingModelSerializer(many=True, required=False)

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
