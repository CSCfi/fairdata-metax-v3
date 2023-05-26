from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers

from apps.actors.models import Actor, Organization
from apps.users.serializers import MetaxUserModelSerializer


class ChildOrganizationSerializer(serializers.ModelSerializer):
    """Serialize child organization tree without repeating parent organization."""

    children = serializers.SerializerMethodField(read_only=True, method_name="get_children")

    def get_children(self, obj):
        serializer = ChildOrganizationSerializer(instance=obj.children.all(), many=True)
        return serializer.data

    class Meta:
        model = Organization
        fields = "__all__"

    def to_representation(self, instance):
        reps = super().to_representation(instance)
        reps.pop("parent")
        return reps


class ParentOrganizationSerializer(serializers.ModelSerializer):
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


class OrganizationSerializer(serializers.ModelSerializer):
    """Serialize organization

    Will include
    * All child organizations
    * Parent organizations up to root, but no children of parents
    """

    children = ChildOrganizationSerializer(many=True, read_only=True)
    parent = ParentOrganizationSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"


class ActorModelSerializer(WritableNestedModelSerializer):
    organization = OrganizationSerializer(many=False, required=False, allow_null=True)

    def create(self, validated_data):
        org = None
        if org_data := validated_data.pop("organization", None):
            org = self.fields["organization"].create(org_data)

        return Actor.objects.create(organization=org, **validated_data)


    class Meta:
        model = Actor
        fields = ("organization", "person")
