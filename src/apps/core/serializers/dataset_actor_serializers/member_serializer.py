import logging
import uuid
from typing import Any, Dict, Optional

from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.helpers import changed_fields, has_values
from apps.common.serializers import CommonNestedModelSerializer
from apps.common.serializers.serializers import StrictSerializer

logger = logging.getLogger(__name__)

from dataclasses import dataclass


@dataclass
class DatasetMemberContext:
    """Helper class for keeping track of members in dataset or being added to dataset."""

    object: models.Model = None  # object instance
    save_data: dict = None  # data used for saving object
    comparison_data: dict = (
        None  # new data with nested objects replaced with id, used for comparisons
    )
    existing_data: dict = None  # like comparison_data but for data already in dataset
    is_existing: bool = False  # member already existed in dataset before request
    is_updated: bool = False  # dataset is already up-to-date, no need to save again
    error: Any = None  # if object has an error, raise it instead of trying to save


class UUIDOrTagField(serializers.UUIDField):
    """Field that accepts UUIDs or '#value' style strings."""

    def to_internal_value(self, data):
        if type(data) is str and data.startswith("#"):
            return data
        return super().to_internal_value(data)

    def to_representation(self, value):
        if type(value) is str and value.startswith("#"):
            return value
        return super().to_representation(value)


class IntegerOrTagField(serializers.IntegerField):
    """Field that accepts integers or '#value' style strings."""

    # TODO: Use UUID default primary keys so only the UUID version is needed
    def to_internal_value(self, data):
        if type(data) is str and data.startswith("#"):
            return data
        return super().to_internal_value(data)

    def to_representation(self, value):
        if type(value) is str and value.startswith("#"):
            return value
        return super().to_representation(value)


class DatasetMemberSerializer(StrictSerializer, CommonNestedModelSerializer):
    """Serialize dataset members that may be in multiple places in same dataset.

    Serializer for actors, persons and organizations that allows same object
    to be used in multiple places in same dataset by `id`.

    The `id` can be
    - an existing object in the dataset
    - a temporary id in format "#somevalue", that will be replaced with an actual id on save.

    Duplicates of objects with an `id` should contain either the same data,
    or only the `id` field to indicate data should be copied there from other duplicates.
    If id is omitted, try to match objects already in dataset and other request
    objects that have no id.

    The serializer works in two phases:

    to_internal_value
    - Ensures each input object has an id (might be a temporary id).
    - Checks that non-temporary ids point to an object existing in dataset.
    - Determines `validated_data` that will be used for updating the object.
      - Note: Kwargs of the save function (i.e. parent relation) are unavailable here.
    save
    - Saves each separate object only once, and other occurrences use the saved instance.

    Subclasses need to define `get_dataset_members` that returns
    mapping of id to DatasetMemberContext instances for existing objects in dataset.
    """

    default_error_messages = {
        **serializers.Serializer.default_error_messages,
        "does_not_exist": _("{model_name} does not exist in dataset {dataset_id}."),
    }

    partial_update_fields = {"id"}  # Fields allowed for partial update

    # Fields that may be updated after object has already been saved once,
    # e.g. parent ForeignKey for multi-parent object
    extra_save_data_fields = set()

    # Validator should return True if data can be used to create new instance
    save_validator = lambda self, value: True

    def get_dataset_members(self) -> Dict[str, DatasetMemberContext]:
        """Implement in subclass."""
        raise NotImplementedError()

    @property
    def model_name(self):
        return self.Meta.model.__name__

    def should_save_data(self, value: Optional[dict]) -> bool:
        """Value contains non-identifying fields, object needs to be updated."""
        if not value:
            return False
        return has_values(value, exclude={"id"})

    def ensure_id(self, attrs, comparison_data) -> str:
        """Assign id to data if one does not exist and return the id."""
        if id := attrs.get("id"):
            attrs["id"] = str(attrs["id"])
            return attrs["id"]

        # no actual or temp id, check for members with identical data (including no id)
        dataset_members = self.get_dataset_members()
        for member_id, member in dataset_members.items():
            if comparison_data is not None and (
                member.comparison_data == comparison_data
                or member.existing_data == comparison_data
            ):
                attrs["id"] = member_id
                return member_id

        # create a new temp id
        id = f"#tmp-id-{uuid.uuid4()}"
        attrs["id"] = id
        return id

    def get_comparison_data(self, value, depth=0):
        """Get data used for comparing objects.

        Objects with same comparison data should be considered the same object.
        When updating objects with same id, all should have same comparison data.
        """
        if not isinstance(value, dict):
            return value

        if depth > 0:
            if id := value.get("id"):
                return str(id)
        return {k: self.get_comparison_data(v, depth + 1) for k, v in value.items()}

    def get_existing_data(self, object):
        """Get comparison data for existing object, used for determining id."""
        old_show_emails = self.context.get("show_emails")
        self.context["show_emails"] = True  # Show emails when getting existing data for comparison
        rep = self.to_representation(object)
        self.context["show_emails"] = old_show_emails

        rep.pop("id", None)
        return self.get_comparison_data(rep)

    def update_save_data(self, member: DatasetMemberContext, validated_data: dict):
        """Update save data based on validated data."""
        if not (
            member.save_data and has_values(member.save_data, exclude=self.partial_update_fields)
        ):
            member.save_data = validated_data

    def validate_comparison_data(self, id, member, comparison_data):
        if (
            member.comparison_data is not None
            and comparison_data is not None
            and comparison_data != member.comparison_data
        ):
            # Data has conflicting values, we should throw error.
            # This also prevents e.g. an organization from being its own parent.
            fields = changed_fields(comparison_data, member.comparison_data)
            errors = {"id": _("Conflicting data for {} {}").format(self.model_name, id)}
            for field in fields:
                errors[field] = _("Value conflicts with another in request")
            raise serializers.ValidationError(errors)

    def get_extra_attrs(self):
        """Data that is provided by parent serializer but is not in a serializer field."""
        if self.parent:
            return getattr(self.parent, "child_extra_attrs", {})
        return {}

    def to_internal_value(self, data) -> dict:
        attrs = super().to_internal_value(data)

        # If doing only partial update, remove default values
        if not has_values(data, exclude=self.partial_update_fields):
            attrs = {key: value for key, value in attrs.items() if key in data}
        attrs.update(self.get_extra_attrs())

        comparison_data = self.get_comparison_data(attrs)
        id = self.ensure_id(attrs, comparison_data)

        dataset_members = self.get_dataset_members()
        member = dataset_members.setdefault(id, DatasetMemberContext())

        is_temp_id = id.startswith("#")
        if not is_temp_id and not member.object:
            # No existing object and not creating a new object
            msg = self.error_messages["does_not_exist"]
            raise serializers.ValidationError(
                {
                    "id": msg.format(
                        model_name=self.model_name, dataset_id=self.context.get("dataset")
                    )
                }
            )

        if self.should_save_data(attrs):
            self.validate_comparison_data(id, member, comparison_data)
            member.comparison_data = comparison_data
            self.update_save_data(member, validated_data=attrs)

        return attrs

    def validate_save(self, validated_data, instance=None):
        """Assign missing fields from existing instance to get final values for validation."""
        if instance:
            validated_data = {**validated_data}
            for field in self.fields:
                if field not in validated_data:
                    validated_data[field] = getattr(instance, field)
                    # Replace model instance with id object
                    if isinstance(validated_data[field], models.Model):
                        validated_data[field] = {"id": validated_data[field].id}

        return self.save_validator(validated_data)

    def save(self, **kwargs) -> models.Model:
        """Save each instance only once.

        NOTE: Reverse foreign keys to parent aren't available until the save step,
        so they are not available in member.save_data. Cases where an object
        might have multiple different parent foreign key values are not currently
        handled here.
        """
        id = str(self.validated_data.get("id", ""))
        dataset_members = self.get_dataset_members()

        member = dataset_members.get(id)
        if member.error:
            raise member.error

        self.instance = member.object
        if member.is_updated or (self.instance and not self.should_save_data(member.save_data)):
            # Instance in DB is already up to date, skip usual save
            return self.instance

        # Determine what validated_data super().save() will have
        self._validated_data.update(member.save_data or {})
        is_temp_id = id.startswith("#")
        if is_temp_id:  # Remove temporary id so an actual one will be generated in save
            self._validated_data.pop("id", None)

        try:
            self.validate_save(self._validated_data, self.instance)
            instance = super().save(**kwargs)
        except serializers.ValidationError as err:
            member.error = err
            raise err

        member.is_updated = True
        member.object = instance

        if is_temp_id:  # new member object with new id
            instance_member = dataset_members.setdefault(str(instance.id), DatasetMemberContext())
            instance_member.object = instance
            instance_member.is_updated = True

        return instance
