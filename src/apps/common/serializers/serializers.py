# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils import model_meta

logger = logging.getLogger(__name__)


class CommonListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        # Map the instance objects by their unique identifiers
        instance_mapping = {obj.id: obj for obj in instance}
        updated_instances = []

        # Perform updates or create new instances
        for item_data in validated_data:
            item_id = item_data.get("id", None)
            if item_id is not None:
                # Update the existing instance
                item_instance = instance_mapping.get(item_id, None)
                if item_instance is not None:
                    item_serializer = self.child._default_class(data=item_data)
                    item_serializer.is_valid(raise_exception=True)
                    updated_instances.append(item_serializer.update(item_instance, item_data))
            else:
                # Create a new instance
                new_item = self.child.create(item_data)
                updated_instances.append(new_item)

        # Delete instances that were not included in the update
        for item in instance:
            if item.id not in [item_data.get("id", None) for item_data in validated_data]:
                item.delete()

        return updated_instances


class StrictSerializer(serializers.Serializer):
    """Serializer that throws an error for unknown fields."""

    def to_internal_value(self, data):
        if unknown_fields := set(data).difference(self.fields):
            raise serializers.ValidationError(
                {field: _("Unknown field") for field in unknown_fields}
            )
        return super().to_internal_value(data)


class PatchModelSerializer(serializers.ModelSerializer):
    """ModelSerializer which allows PUT (full replacement) and PATCH (partial update) behavior.

    For partial updates, use patch=True which makes all fields non-required.
    This differs from DRF partial=True in that it applies only to the root serializer,
    not to fields in nested serializers. Using partial=True throws a ValueError
    to prevent accidentally using the default partial update style.

    When patch=False, unspecified fields use
    - empty list for many-relations
    - model default value for other values

    For a viewset that uses patch=True for partial updates, see PatchModelMixin.
    """

    def __init__(self, *args, **kwargs):
        self.patch = kwargs.pop("patch", False)
        if kwargs.get("partial"):
            raise ValueError(
                _(
                    "PatchModelSerializer should not be used with partial=True. "
                    "Use patch=True instead"
                )
            )
        super().__init__(*args, **kwargs)

    def assign_defaults_from_model(self, fields):
        """Set default serializer field values from model fields.

        Used for PUT-style update where fields that are not included in
        the update are reset to their default values."""
        for name, field in fields.items():
            if name == "id" or field.required or field.read_only or (field.default is not empty):
                continue

            try:
                source = field.source or name
                model_field = self.Meta.model._meta.get_field(source)
                if model_field.one_to_many or model_field.many_to_many:
                    field.default = []
                elif model_field.is_relation:
                    field.default = None
                elif model_field.has_default():
                    field.default = model_field.get_default()
                elif model_field.null:
                    field.default = None
            except FieldDoesNotExist:
                pass
        return fields

    def get_fields(self):
        """When patch is enabled, no fields are required."""
        fields = super().get_fields()
        if self.patch:
            for field in fields.values():
                field.required = False
                if not field.read_only:
                    field.default = empty
        else:
            fields = self.assign_defaults_from_model(fields)
        return fields


class IncludeRemovedQueryParamsSerializer(serializers.Serializer):
    include_removed = serializers.BooleanField(
        default=False, help_text=_("Include removed items in query.")
    )


class DeleteListQueryParamsSerializer(serializers.Serializer):
    """Non-filter query parameters for deleting a list."""

    flush = serializers.BooleanField(required=False, default=False)


class DeleteListReturnValueSerializer(serializers.Serializer):
    """Serializer (for swagger purposes) for return value of list delete operation."""

    count = serializers.IntegerField(read_only=True)


class NestedModelSerializer(serializers.ModelSerializer):
    """Serializer for nested models.

    Calls create or update methods for nested serializer fields
    where the field source is a model relation.

    Adds current instance to validated_data for reverse related fields.
    E.g. dataset.provenance serializer will have the parent
    dataset object in validated_data as {"dataset": dataset}.

    To indicate that field has alread been processed and should be ignored
    in nested create/update, pop the value from validated_data before calling
    create/update.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get writable serializer fields that correspond to a relation
        model_class = self.Meta.model
        self.model_field_info = model_meta.get_field_info(model_class)

        self.relation_serializers = {}
        self.forward_serializers = {}
        self.reverse_serializers = {}
        self.many_serializers = {}

        for name, field in self.fields.items():
            is_nested_serializer = (
                isinstance(field, serializers.BaseSerializer)
                and (field.source in self.model_field_info.relations)
                and not field.read_only
            )
            if is_nested_serializer:
                relation_info = self.model_field_info.relations[field.source]
                self.relation_serializers[name] = field
                if relation_info.to_many:
                    self.many_serializers[name] = field
                elif relation_info.reverse:
                    self.reverse_serializers[name] = field
                else:
                    self.forward_serializers[name] = field

    def get_reverse_field(self, serializer):
        model_class = self.Meta.model
        return model_class._meta.get_field(serializer.source).remote_field

    def inject_instance_to_data(self, serializer, instance, field_data):
        """Inject parent instance to reverse relation data.

        ForeignKey and OneToOne relations defined from child model to parent
        model need to be assigned to the child instance. This method adds
        the parent instance to the data passed to child serializer.

        E.g. when calling `SerializerA.save` for
        ```
        class SerializerA(NestedModelSerializer):
            b = SerializerB()

        class SerializerB(ModelSerializer):
            a = PrimaryKeyRelatedField()
        ```
        the data for nested update of a.b will have {"a": a} in validated_data.
        """
        reverse_field = self.get_reverse_field(serializer)
        if reverse_field.concrete and not reverse_field.many_to_many:
            # field is defined on the other model and can be assigned directly
            if isinstance(field_data, dict):
                field_data[reverse_field.name] = instance
            elif isinstance(field_data, list):
                for val in field_data:
                    val[reverse_field.name] = instance

    def create_related(self, serializers, instance, related_data):
        """Create related model instances.

        Instance should be None for simple forward relations."""
        related_instances = {}
        for serializer in serializers.values():
            data = related_data.pop(serializer.field_name, None)
            if data is not None:
                if instance:
                    self.inject_instance_to_data(serializer, instance, data)
                serializer.instance = (
                    None  # clear instance to avoid issues when serializer is reused
                )
                serializer._validated_data = data
                serializer._errors = []  # data was already validated by parent serializer
                related_instances[serializer.source] = serializer.save()
        return related_instances

    def get_related_instance(self, serializer, instance):
        """Get related field value from model instance.

        Uses hasattr check to avoid ObjectDoesNotExist for reverse one-to-one fields.
        """
        source = serializer.source
        return hasattr(instance, source) and getattr(instance, source) or None

    def clear_related_instance(self, serializer, related_instance) -> None:
        """Clear related object instance.

        (Soft) deletes a related object. For reverse related concrete field,
        assign null if allowed, otherwise throw error.
        """
        reverse_field = self.get_reverse_field(serializer)
        if reverse_field.concrete:
            # Raise error when trying to clear non-nullable relation on child
            if not reverse_field.null:
                raise serializers.ValidationError(
                    {serializer.field_name: _("Clearing existing value is not allowed.")}
                )
            setattr(related_instance, reverse_field.name, None)
            related_instance.save(update_fields=[reverse_field.name])
        related_instance.delete()  # May be soft delete
        return None

    def update_related(self, nested_serializers, instance, related_data):
        """Update related model instances."""
        related_instances = {}
        for serializer in nested_serializers.values():
            if serializer.field_name not in related_data:
                continue  # data missing from related_data, ignore field

            data = related_data.pop(serializer.field_name)
            self.inject_instance_to_data(serializer, instance, data)

            related_instance = self.get_related_instance(serializer, instance)
            if isinstance(related_instance, models.Manager):
                # Convert manager to iterable
                related_instance = related_instance.all()

            if data is not None:
                serializer.instance = related_instance
                serializer._validated_data = data
                serializer._errors = []  # data was already validated by parent serializer
                related_instance = serializer.save()
            elif related_instance:
                related_instance = self.clear_related_instance(serializer, related_instance)

            related_instances[serializer.source] = related_instance
        return related_instances

    def pop_related_data(self, validated_data):
        """Pop nested serializer data from validated_data."""
        return {
            name: validated_data.pop(serializer.source)
            for name, serializer in self.relation_serializers.items()
            if serializer.source in validated_data
        }

    def create(self, validated_data):
        related_data = self.pop_related_data(validated_data)

        # Create forward related objects
        forward_instances = self.create_related(
            self.forward_serializers, instance=None, related_data=related_data
        )

        # Create instance, assign forward one-to-one and many-to-one relations
        instance = super().create(validated_data={**validated_data, **forward_instances})

        # Create reverse related objects
        self.create_related(self.reverse_serializers, instance=instance, related_data=related_data)

        # Create one-to-many and many-to-many relations
        many_instances = self.create_related(
            self.many_serializers, instance=instance, related_data=related_data
        )

        # Assign many-to-many relations
        for source, related_instance in many_instances.items():
            is_many_to_many = self.model_field_info.relations[source].to_field is None
            if is_many_to_many:
                model_field = getattr(instance, source)
                model_field.set(related_instance)

        return instance

    def update(self, instance, validated_data):
        related_data = self.pop_related_data(validated_data)

        # Update forward related objects
        forward_instances = self.update_related(
            self.forward_serializers, instance=instance, related_data=related_data
        )

        # Update instance, assign forward one-to-one and many-to-one relations
        instance = super().update(
            instance=instance, validated_data={**validated_data, **forward_instances}
        )
        # Update reverse one-to-one related objects
        self.update_related(self.reverse_serializers, instance=instance, related_data=related_data)

        # Update one-to-many and many-to-many objects
        many_instances = self.update_related(
            self.many_serializers, instance=instance, related_data=related_data
        )
        for source, related_instance in many_instances.items():
            model_field = getattr(instance, source)
            model_field.set(related_instance)  # Assign new relations

        return instance


class CommonModelSerializer(PatchModelSerializer, serializers.ModelSerializer):
    """ModelSerializer for behavior common for all model APIs."""


class CommonNestedModelSerializer(CommonModelSerializer, NestedModelSerializer):
    """NestedModelSerializer for behavior common for all model APIs."""


class AbstractDatasetModelSerializer(CommonModelSerializer):
    class Meta:
        fields = "__all__"


class AbstractDatasetPropertyModelSerializer(CommonModelSerializer):
    class Meta:
        fields = ("id", "url", "title")

    def to_representation(self, instance):
        if isinstance(instance.title, str):
            instance.title = json.loads(instance.title)
        representation = super().to_representation(instance)

        return representation

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        if "id" in data:
            try:
                UUID(data.get("id"))
                internal_value["id"] = data.get("id")
            except ValueError:
                raise serializers.ValidationError(
                    _("id: {} is not valid UUID").format(data.get("id"))
                )

        return internal_value
