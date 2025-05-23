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
from typing import Any, Dict, Iterable, List, Mapping, Optional, Type
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.compat import postgres_fields
from rest_framework.fields import empty
from rest_framework.serializers import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import html, model_meta

from apps.common.serializers.fields import (
    CommaSeparatedListField,
    MultiLanguageField,
    NullableCharField,
    PrivateEmailField,
)

logger = logging.getLogger(__name__)


def parse_html_data_to_list(data):
    if html.is_html_input(data):
        return html.parse_html_list(data, default=[])
    return data


class CommonListSerializer(serializers.ListSerializer):
    def preprocess(self, data):
        """Call preprocess method of child if available."""
        if not isinstance(data, list):  # Ensure data is a list
            return

        if preprocess := getattr(self.child, "preprocess", None):
            for item in data:
                preprocess(item)

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
        if not self.parent:  # Root serializer calls preprocess
            self.preprocess(data)

        data = parse_html_data_to_list(data)

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

    def _delete_instances(self, instances: Iterable[models.Model]):
        """Delete instances, use lazy deleting if enabled."""
        if not instances:
            return
        if self.child.lazy:  # Delete at end of deserialization
            lazy_saver = LazyInstanceSaver.get_from_context(self.context)
            for item in instances:
                lazy_saver.add_delete(item)
        else:  # Delete immediately
            for item in instances:
                item.delete()

    def update(self, instance: Iterable[models.Model], validated_data):
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
        updated_ids = {str(item_data.get("id", None)) for item_data in validated_data}
        self._delete_instances([item for item in instance if str(item.id) not in updated_ids])
        return updated_instances


class UpdatingListSerializer(CommonListSerializer):
    """CommonListSerializer that updates existing instances based on list position.

    Updating values instead of creating new objects and deleting the old ones
    makes ids more stable. The downside is that deleting an item
    will cause the item to be updated with values from the next item.

    For example, updating [item1, item2] with [values1, values2, values3] will
    update values of item1 and item2 and create item3.
    Any values not set by the serializer will remain, so omitting values2 would mean
    item2 is updated with values3 but has e.g. the original creation timestamp.
    """

    def update(self, instance: Iterable[models.Model], validated_data):
        instances = [obj for obj in instance]

        # Perform updates or create new instances
        item_serializer = self.child
        errors = []  # Collect errors to match serializer validation reporting error style
        updated_instances = []
        for idx, item_data in enumerate(validated_data):
            if idx < len(instances):
                item_serializer.instance = instances[idx]  # Update existing
            else:
                item_serializer.instance = None  # Create a new instance
            try:
                item_serializer._validated_data = item_data
                item_serializer._errors = []  # data was already validated by parent serializer
                updated_instances.append(item_serializer.save())
                errors.append({})
            except serializers.ValidationError as exc:
                errors.append(exc.detail)

        if any(errors):
            raise ValidationError(errors)

        # Delete instances that were not included in the update
        self._delete_instances(instances[len(updated_instances) :])
        return updated_instances


class StrictSerializer(serializers.Serializer):
    """Serializer that throws an error for unknown fields."""

    def run_validation(self, data=empty):
        if self.context.get("strict", True) and isinstance(data, dict):
            unknown_keys = set(data.keys()) - set(self.fields.keys())
            if unknown_keys:
                raise ValidationError({key: ["Unexpected field"] for key in unknown_keys})

        return super().run_validation(data=data)


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

    def assign_defaults_from_model(self, fields: dict):
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


class FieldsQueryParamsSerializer(serializers.Serializer):
    """Non-filter query parameters for deleting a list."""

    fields = CommaSeparatedListField(
        required=False, help_text=_("Filter specific fields of the dataset.")
    )


class DeleteListReturnValueSerializer(serializers.Serializer):
    """Serializer (for swagger purposes) for return value of list delete operation."""

    count = serializers.IntegerField(read_only=True)


class LazyInstanceSaver:
    """LazyInstanceSaver bulk upserts deserialized model instances at the end of deserialization."""

    def __init__(self):
        self.upserts_by_serializer: Dict[serializers.Serializer, models.Model] = {}
        self.deletes_by_model: Dict[Type[models.Model], models.Model] = {}

    @classmethod
    def create_in_context(cls, context: dict):
        self = cls()
        context["lazy_saver"] = self

    @classmethod
    def get_from_context(cls, context) -> "LazyInstanceSaver":
        if saver := context.get("lazy_saver"):
            return saver
        raise ValueError("LazyInstanceSaver not found in serializer context.")

    def add_upsert(self, serializer: serializers.Serializer, instance: models.Model):
        """Add model instance to be saved later."""
        instances = self.upserts_by_serializer.setdefault(serializer, [])
        instances.append(instance)

    def add_delete(self, instance: models.Model):
        """Add model instance to be deleted later."""
        instances = self.deletes_by_model.setdefault(instance.__class__, [])
        instances.append(instance)

    def save(self):
        """Save added instances."""
        # Perform bulk upsert for each serializer instance
        for serializer, instances in self.upserts_by_serializer.items():
            model: models.Model = serializer.Meta.model
            concrete_fields = {
                f.name for f in model._meta.get_fields() if f.concrete and not f.many_to_many
            }
            update_fields = [
                f.source
                for f in serializer._writable_fields
                if f.source in concrete_fields and f.source != "id"
            ]
            model.objects.bulk_create(
                instances,
                update_conflicts=True,
                update_fields=update_fields,
                unique_fields=["id"],
            )

        # Perform bulk delete for each model
        for model, instances in self.deletes_by_model.items():
            model.objects.filter(id__in=[i.id for i in instances]).delete()


class LazyableModelSerializer(serializers.ModelSerializer):
    """LazyableModelSerializer allows model instances to be bulk upserted at end of serialization.

    When lazy is True, creating or updating an instance does not save the instance to
    the database. Instead, the instance is added to the LazyInstanceSaver (created by
    the root serializer) in the serializer context.

    Lazy instances have several restrictions, including:
    - Saving a ForeignKey to a lazy instance requires a transaction
    - Lazy instances are not actually in the database until end of transaction
    - Model.save is not called for lazy instances
    - Save signals are not sent for lazy instances

    Lazy serializers may contain non-lazy nested serializer fields.
    """

    def __init__(self, *args, lazy=False, **kwargs):
        # Lazy serializer does not save the created or updated instance
        # but passes the instances to a LazyInstanceSaver from context.
        self.lazy = lazy
        super().__init__(*args, **kwargs)

    def create(self, validated_data):
        if self.lazy:
            saver = LazyInstanceSaver.get_from_context(self.context)
            instance = self.Meta.model(**validated_data)
            saver.add_upsert(self, instance)  # Instance will be saved later
            return instance

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if self.lazy:
            saver = LazyInstanceSaver.get_from_context(self.context)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            saver.add_upsert(self, instance)  # Instance will be saved later
        return super().update(instance, validated_data)


class NestedModelSerializer(LazyableModelSerializer):
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
        self.has_relation_info = False

    def collect_relation_info(self):
        """Collect information about nested relations."""
        if self.has_relation_info:
            return

        # Get writable serializer fields that correspond to a relation
        model_class = self.Meta.model
        self.model_field_info = model_meta.get_field_info(model_class)

        self.relation_serializers = {}
        self.forward_serializers = {}
        self.reverse_serializers = {}
        self.many_serializers = {}
        self.lazy_serializers = {}

        for name, field in self.fields.items():
            actual_field = getattr(field, "child", None) or field
            if getattr(actual_field, "lazy", False):
                self.lazy_serializers[name] = field

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

        self.has_relation_info = True

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
        if serializer.lazy:
            LazyInstanceSaver.get_from_context(self.context).add_delete(related_instance)
        else:
            related_instance.delete()  # May be soft delete
        return None

    def check_lazy_transaction(self):
        """Warn if save is called outside a transaction if there are lazy serializer fields.

        Django foreign key contraints are created with DEFERRABLE INITIALLY DEFERRED,
        which means they are not checked until the end of the transaction. This means
        saving a foreign key to an unsaved instance will work as long as the instance
        gets saved before the transaction ends.
        """
        if self.lazy_serializers and transaction.get_autocommit():
            fields = ", ".join(self.lazy_serializers)
            logger.warning(
                f"{self.__class__.__name__} has lazy serializer fields ({fields}) "
                "and should update in a transaction."
            )

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
        self.collect_relation_info()
        self.check_lazy_transaction()
        if self.parent is None:  # Root serializer handles lazy save
            LazyInstanceSaver.create_in_context(self.context)

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
            if not related_instance:
                # Ignore empty list because the m2m relation should already
                # be empty for a newly created object
                continue
            model_field = self.model_field_info.relations[source].model_field
            is_many_to_many = model_field and model_field.many_to_many
            if is_many_to_many:
                instance_field = getattr(instance, source)
                instance_field.set(related_instance)

        if self.parent is None:  # Root serializer handles lazy save
            LazyInstanceSaver.get_from_context(self.context).save()
        return instance

    def update(self, instance, validated_data):
        self.collect_relation_info()
        self.check_lazy_transaction()
        if self.parent is None:  # Root serializer handles lazy save
            LazyInstanceSaver.create_in_context(self.context)

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
            model_field = self.model_field_info.relations[source].model_field
            is_many_to_many = model_field and model_field.many_to_many
            if is_many_to_many:
                instance_field = getattr(instance, source)
                instance_field.set(related_instance)

        # Update instance, assign forward one-to-one and many-to-one relations
        instance = super().update(
            instance=instance, validated_data={**validated_data, **forward_instances}
        )

        if self.parent is None:  # Root serializer handles lazy save
            LazyInstanceSaver.get_from_context(self.context).save()
        return instance


class CommonModelSerializer(StrictSerializer, PatchModelSerializer, LazyableModelSerializer):
    """ModelSerializer for behavior common for all model APIs."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        # Default to using MultiLanguageField serializer field for all HStoreFields
        postgres_fields.HStoreField: MultiLanguageField,
        # Default to using NullableCharField for CharField and TextField
        models.CharField: NullableCharField,
        models.TextField: NullableCharField,
        # Hide emails by default
        models.EmailField: PrivateEmailField,
    }

    def preprocess(self, data):
        """Call preprocess method of nested fields where available.

        The preprocess step is an extra step before to_internal_value
        that allows a field to e.g. collect all required reference data identifiers
        in preprocess and then get the data in a single query in to_internal_value.
        """
        if data is None:
            return

        if not isinstance(data, Mapping):
            message = self.error_messages["invalid"].format(datatype=type(data).__name__)
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]}, code="invalid")
        fields = self._writable_fields
        for field in fields:
            # Check for preprocess method, call it with field value
            if preprocess := getattr(field, "preprocess", None):
                primitive_value = field.get_value(data)
                if primitive_value is not empty:
                    preprocess(primitive_value)

    def to_internal_value(self, data):
        if not self.parent:  # Root serializer calls preprocess
            self.preprocess(data)
        return super().to_internal_value(data)

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

    def __init__(self, help_text=None):
        super().__init__(required=False, allow_null=True, help_text=help_text)
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
