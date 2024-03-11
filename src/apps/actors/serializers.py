import logging

from rest_framework import serializers

from apps.actors.models import Actor, HomePage, Organization, Person
from apps.common.serializers import CommonListSerializer
from apps.common.serializers.serializers import CommonModelSerializer

logger = logging.getLogger("__name__")


class HomePageSerializer(CommonModelSerializer):
    """Serialize parent organizations up to root."""

    class Meta:
        model = HomePage
        fields = ["title", "url"]


def get_org_children(context: dict, org: Organization):
    """Serialize reference data childen of organization."""
    # Return only children that match the deprecation status of the parent
    if org.deprecated:
        children = [
            child for child in org.children.all() if child.is_reference_data and child.deprecated
        ]
    else:
        children = [
            child
            for child in org.children.all()
            if child.is_reference_data and not child.deprecated
        ]
    serializer = ChildOrganizationSerializer(instance=children, many=True, context=context)
    return serializer.data


class ChildOrganizationSerializer(CommonModelSerializer):
    """Serialize child organization tree without repeating parent organization."""

    children = serializers.SerializerMethodField(read_only=True, method_name="get_children")

    def get_children(self, obj):
        return get_org_children(self.context, obj)

    class Meta:
        model = Organization
        fields = "__all__"

    def to_representation(self, instance):
        if not self.context.get("expand_child_organizations"):
            return instance.id

        reps = super().to_representation(instance)
        reps.pop("parent")
        return reps


class ParentOrganizationSerializer(CommonModelSerializer):
    """Serialize parent organizations up to root."""

    parent = serializers.SerializerMethodField(read_only=True, method_name="get_parent")

    def get_parent(self, obj):
        if obj.parent:
            serializer = ParentOrganizationSerializer(instance=obj.parent)
            return serializer.data
        return None

    class Meta:
        model = Organization
        fields = "__all__"


class OrganizationSerializer(CommonModelSerializer):
    """Serialize organization

    Will include
    * All child organizations
    * Parent organizations up to root, but no children of parents
    """

    children = serializers.SerializerMethodField(read_only=True, method_name="get_children")
    parent = ParentOrganizationSerializer(read_only=True)
    homepage = HomePageSerializer(read_only=True)

    def get_children(self, obj):
        return get_org_children(self.context, obj)

    class Meta:
        model = Organization
        fields = "__all__"


class CompactOrganizationSerializer(OrganizationSerializer):
    """Serialize organization

    Will exclude
    * child organizations
    * created
    * modified
    * removed
    """

    parent = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Organization
        fields = ("parent", "pref_label", "url", "in_scheme")

    def get_parent(self, child):
        if not child.parent:
            return None
        return CompactOrganizationSerializer(instance=child.parent).data


class PersonModelSerializer(CommonModelSerializer):
    class Meta:
        model = Person
        fields = ("id", "name", "email", "external_identifier")


class ActorModelSerializer(CommonModelSerializer):
    organization = OrganizationSerializer(many=False, required=False, allow_null=True)
    person = PersonModelSerializer(many=False, required=False, allow_null=True)

    def create(self, validated_data):
        org = None
        person = None

        if org_data := validated_data.pop("organization", None):
            org = self.fields["organization"].create(org_data)
        if person_data := validated_data.pop("person", None):
            person = self.fields["person"].create(person_data)

        return Actor.objects.create(organization=org, person=person, **validated_data)

    def update(self, instance, validated_data):
        if org_data := validated_data.pop("organization", None):
            self.fields["organization"].update(instance.organization, org_data)
        return super().update(instance, validated_data)

    class Meta:
        model = Actor
        fields = ("organization", "person", "id")
        read_only_fields = ("id",)
        list_serializer_class = CommonListSerializer
