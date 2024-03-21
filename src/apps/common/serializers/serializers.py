# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import copy
import json
import logging
from contextlib import contextmanager
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.compat import postgres_fields
from rest_framework.fields import empty
from rest_framework.serializers import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import html, model_meta

from apps.common.serializers.fields import MultiLanguageField, PrivateEmailField

logger = logging.getLogger(__name__)


class CommonListSerializer(serializers.ListSerializer):
    def get_child_ordering_field(self):
        """Get field which is used for order value of child model.

        For example, child serializer with
        ```
        class Meta:
            ordering_fields = {"Dataset.actors": "actors_order"}
        ```
        will have `self.parent.child_extra_attrs = {"actors_order": idx}`
        during validation, where `idx` is the position in `actors` list
        of `Dataset` serializer. This can then be used in
        `to_internal_value` of the child to assign the list position.

        Note: When calling the list serializer directly (not nested),
        the parent and field name information is missing. Supporting
        such cases needs further develpment.
        """
        parent_name = ""
        try:
            parent_name = self.parent.Meta.model.__name__ + "."
        except AttributeError:
            pass
        field_key = f"{parent_name}{self.field_name}"  # e.g. "Dataset.actors"

        try:
            return self.child.Meta.ordering_fields.get(field_key)
        except AttributeError:
            pass

        return None

    def to_internal_value(self, data):
        """Same as original to_internal_value but with ordering field in child_extra_attrs."""
        if html.is_html_input(data):
            data = html.parse_html_list(data, default=[])

        if not isinstance(data, list):
            message = self.error_messages["not_a_list"].format(input_type=type(data).__name__)
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [message]}, code="not_a_list"
            )

        if not self.allow_empty and len(data) == 0:
            message = self.error_messages["empty"]
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]}, code="empty")

        if self.max_length is not None and len(data) > self.max_length:
            message = self.error_messages["max_length"].format(max_length=self.max_length)
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [message]}, code="max_length"
            )

        if self.min_length is not None and len(data) < self.min_length:
            message = self.error_messages["min_length"].format(min_length=self.min_length)
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [message]}, code="min_length"
            )

        ret = []
        errors = []

        self.child_extra_attrs = {}
        ordering_field = self.get_child_ordering_field()
        for idx, item in enumerate(data):
            if ordering_field:
                self.child_extra_attrs = {ordering_field: idx}
            try:
                validated = self.child.run_validation(item)
            except ValidationError as exc:
                errors.append(exc.detail)
            else:
                ret.append(validated)
                errors.append({})

        if any(errors):
            raise ValidationError(errors)

        return ret

    def create(self, validated_data):
        errors = []  # Collect errors to match serializer validation reporting error style
        instances = []

        # Create new instances
        item_serializer = self.child
        for item_data in validated_data:
            try:
                item_serializer.instance = None  # Create a new instance
                item_serializer._validated_data = item_data
                item_serializer._errors = []  # data was already validated by parent serializer
                instances.append(item_serializer.save())
                errors.append({})
            except serializers.ValidationError as exc:
                errors.append(exc.detail)
        if any(errors):
            raise ValidationError(errors)

        return instances

    def update(self, instance, validated_data):
        # Map the instance objects by their unique identifiers
        instance_mapping = {obj.id: obj for obj in instance}
        updated_instances = []

        # Perform updates or create new instances
        item_serializer = self.child
        errors = []  # Collect errors to match serializer validation reporting error style
        for item_data in validated_data:
            try:
                item_id = item_data.get("id", None)
                if item_id is not None:
                    # Update the existing instance
                    item_serializer.instance = instance_mapping.get(item_id, None)
                else:
                    item_serializer.instance = None  # Create a new instance

                item_serializer._validated_data = item_data
                item_serializer._errors = []  # data was already validated by parent serializer
                updated_instances.append(item_serializer.save())
                errors.append({})
            except serializers.ValidationError as exc:
                errors.append(exc.detail)

        if any(errors):
            raise ValidationError(errors)

        # Delete instances that were not included in the update
        updated_items = {str(item_data.get("id", None)) for item_data in validated_data}
        for item in instance:
            if str(item.id) not in updated_items:
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

    # Fields that don't get default assigned when using PUT
    no_put_default_fields = {"id"}

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
            if (
                name in self.no_put_default_fields
                or field.required
                or field.read_only
                or (field.default is not empty)
            ):
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


class FlushQueryParamsSerializer(serializers.Serializer):
    """Non-filter query parameters for deleting a list."""

    flush = serializers.BooleanField(
        required=False, default=False, help_text=_("Completely remove object from database.")
    )


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
        errors = {}  # Collect errors that happen during save
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

                try:
                    related_instances[serializer.source] = serializer.save()
                except ValidationError as exc:
                    errors[serializer.field_name] = exc.detail  # Report validation errors by field
        if errors:
            raise ValidationError(errors)
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
        errors = {}  # Collect errors that happen during save
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

                try:
                    related_instance = serializer.save()
                except ValidationError as exc:
                    errors[serializer.field_name] = exc.detail  # Report validation errors by field

            elif related_instance:
                related_instance = self.clear_related_instance(serializer, related_instance)

            related_instances[serializer.source] = related_instance

        if errors:
            raise ValidationError(errors)
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

        # Update reverse one-to-one related objects
        self.update_related(self.reverse_serializers, instance=instance, related_data=related_data)

        # Update one-to-many and many-to-many objects
        many_instances = self.update_related(
            self.many_serializers, instance=instance, related_data=related_data
        )
        for source, related_instance in many_instances.items():
            model_field = getattr(instance, source)
            model_field.set(related_instance)  # Assign new relations

        # Update instance, assign forward one-to-one and many-to-one relations
        instance = super().update(
            instance=instance, validated_data={**validated_data, **forward_instances}
        )
        return instance


class CommonModelSerializer(PatchModelSerializer, serializers.ModelSerializer):
    """ModelSerializer for behavior common for all model APIs."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        # Default to using MultiLanguageField serializer field for all HStoreFields
        postgres_fields.HStoreField: MultiLanguageField,
        # Hide emails by default
        models.EmailField: PrivateEmailField,
    }

    @property
    def _readable_fields(self):
        for field in super()._readable_fields:
            # Unlike get_fields which is common for all items in a list serializer,
            # _readable_fields is run for each item in to_representation so
            # we can have a different context for each item
            if isinstance(field, PrivateEmailField):
                # Hide email fields from responses by default
                if not self.context.get("show_emails"):
                    continue
            yield field

    def create(self, validated_data):
        instance = super().create(validated_data)
        if create_snapshot := getattr(instance, "create_snapshot", None):
            create_snapshot(created=True)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if create_snapshot := getattr(instance, "create_snapshot", None):
            create_snapshot()
        return instance

    def validate(self, data):
        if self.context.get("strict") and hasattr(self, "initial_data"):
            unknown_keys = set(self.initial_data.keys()) - set(self.fields.keys())
            if unknown_keys:
                raise ValidationError({key: "Unexpected field" for key in unknown_keys})
        return super().validate(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if not self.context.get("include_nulls"):
            rep = {k: v for k, v in rep.items() if v is not None}
        return rep


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


class RecursiveSerializer(serializers.Serializer):
    """Serializer that reuses its parent serializer recursively.

    Note: Does not currently support `many=True`.
    """

    def __init__(self):
        super().__init__(required=False, allow_null=True)
        self.serializer = None

    @contextmanager
    def push_serializer_attrs(self):
        """Store serializer attributes before assigning them from self."""
        try:
            prev_instance = self.serializer.instance
            prev_errors = getattr(self.serializer, "_errors", None)
            prev_validated_data = getattr(self.serializer, "_validated_data", None)
            self.serializer.instance = self.instance
            self.serializer._errors = self._errors
            self.serializer._validated_data = self._validated_data
            yield
        finally:
            self.instance = self.serializer.instance
            self._errors = self.serializer._errors
            self._validated_data = self.serializer._validated_data
            self.serializer.instance = prev_instance
            self.serializer._errors = prev_errors
            self.serializer._validated_data = prev_validated_data

    def ensure_serializer(self):
        """Parent is not available in init so we copy it later when needed."""
        if not self.serializer:
            # Copy parent serializer so it can be assigned a different field_name
            self.serializer = copy.deepcopy(self.parent)
            self.serializer.field_name = self.field_name
            self.serializer.parent = self.parent

    def save(self, **kwargs):
        self.ensure_serializer()
        with self.push_serializer_attrs():
            self.serializer.save(**kwargs)
        return self.instance

    def create(self, validated_data):
        self.ensure_serializer()
        return self.serializer.create(validated_data)

    def update(self, validated_data, instance):
        self.ensure_serializer()
        return self.serializer.update(validated_data, instance)

    def to_internal_value(self, data):
        self.ensure_serializer()
        return self.serializer.to_internal_value(data)

    def to_representation(self, instance):
        self.ensure_serializer()
        return self.serializer.to_representation(instance)
