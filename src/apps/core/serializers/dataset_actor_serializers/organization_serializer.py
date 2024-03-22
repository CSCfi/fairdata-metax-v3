import logging
from typing import Any, Dict, Tuple

from django.db.models.base import Model as Model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.actors.models import Organization
from apps.actors.serializers import HomePageSerializer
from apps.common.helpers import is_valid_uuid
from apps.common.serializers.serializers import CommonListSerializer, RecursiveSerializer
from apps.common.serializers.validators import AllOf
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.serializers.dataset_actor_serializers.member_serializer import (
    DatasetMemberContext,
    DatasetMemberSerializer,
    UUIDOrTagField,
)

logger = logging.getLogger(__name__)


class DatasetOrganizationSerializer(DatasetMemberSerializer):
    """Dataset member organization serializer."""

    id = UUIDOrTagField(required=False)
    parent = RecursiveSerializer()
    homepage = HomePageSerializer(required=False, allow_null=True)

    default_error_messages = {
        **DatasetMemberSerializer.default_error_messages,
        "does_not_exist": _(
            "{model_name} is not reference data and does not exist in dataset {dataset_id}."
        ),
    }
    save_validator = AllOf(["pref_label"])

    class Meta:
        model = Organization
        fields = (
            "id",
            "pref_label",
            "url",
            "in_scheme",
            "external_identifier",
            "parent",
            "homepage",
            "email",
        )
        extra_kwargs = {
            "pref_label": {"required": False},  # checked by save_validator
        }
        list_serializer_class = CommonListSerializer

    def to_internal_value(self, data):
        data.pop("in_scheme", None)  # ignore in_scheme
        return super().to_internal_value(data)

    def get_dataset_organizations(self, dataset) -> Dict[str, DatasetMemberContext]:
        """Get DatasetMemberContext for all organizations in dataset."""
        orgs = {}

        def add_org(org):
            if org:
                orgs[str(org.id)] = DatasetMemberContext(
                    object=org,
                    is_existing=True,
                    is_updated=org.is_reference_data,  # don't update refdata orgs
                    existing_data=self.get_existing_data(org),
                )
                add_org(org.parent)

        for actor in dataset.actors.all():
            add_org(actor.organization)

        for provenance in dataset.provenance.all():
            for actor in provenance.is_associated_with.all():
                add_org(actor.organization)

        for project in dataset.projects.all():
            for org in project.participating_organizations.all():
                add_org(org)

            for funding in project.funding.all():
                if funding.funder:
                    add_org(funding.funder.organization)

        return orgs

    def get_dataset_members(self) -> Dict[str, DatasetMemberContext]:
        if "dataset_organizations" not in self.context:
            dataset: Dataset = self.context.get("dataset")
            if dataset:
                self.context["dataset_organizations"] = self.get_dataset_organizations(dataset)
            else:
                self.context["dataset_organizations"] = {}
        return self.context["dataset_organizations"]

    def check_reference_data(self, attrs: dict, comparison_data: dict):
        """Get org from reference data if possible.

        If data `id` or `url` points to reference data,
        assign that `id` to attrs.
        """
        id = str(attrs.get("id", ""))
        url = attrs.get("url", None)
        if (id and not is_valid_uuid(id)) or not (url or id):
            attrs.pop("url", None)  # url not needed afterwards
            return attrs

        dataset_members = self.get_dataset_members()
        member = dataset_members.get(id)
        if member and not url:
            if member.object and member.object.is_reference_data:
                comparison_data.clear()  # no need to compare anything for reference data
            return attrs  # org found, no url to validate

        # Check if id and/or url belong to reference data
        query_args = {"is_reference_data": True}
        if id:
            query_args["id"] = id
        if url:
            query_args["url"] = url
        try:
            instance = Organization.objects.get(**query_args)
            return self.handle_found_reference_data(instance, attrs, comparison_data)

        except Organization.DoesNotExist:
            require_refdata = "url" in query_args  # only refdata can have url
            if require_refdata:
                return self.handle_missing_reference_data(attrs, comparison_data)

        return attrs

    def handle_found_reference_data(
        self, instance: Organization, attrs: dict, comparison_data: dict
    ):
        instance_id = str(instance.id)
        attrs["id"] = instance_id
        dataset_members = self.get_dataset_members()
        member = dataset_members.setdefault(instance_id, DatasetMemberContext())
        member.object = instance
        member.is_updated = True  # don't update refdata
        comparison_data.clear()  # no need to compare anything for reference data
        return attrs

    def handle_missing_reference_data(self, attrs: dict, comparison_data: dict):
        raise serializers.ValidationError(
            {"url": _("Reference organization matching query does not exist.")}
        )

    def ensure_id(self, attrs, comparison_data) -> Tuple[Any, bool]:
        self.check_reference_data(attrs, comparison_data)
        return super().ensure_id(attrs, comparison_data)
