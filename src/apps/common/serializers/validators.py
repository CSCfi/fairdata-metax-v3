from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class RequiredFieldCombinationValidatorBase:
    def __init__(self, fields, count_all_falsy=False):
        self.fields = set(fields)
        self.count_all_falsy = count_all_falsy

    @property
    def msg_fields(self):
        return ", ".join(f"'{f}'" for f in sorted(self.fields))

    def field_value_count(self, value):
        """Count how many non-empty field values exist."""
        if self.count_all_falsy:
            return sum(1 for key, v in value.items() if key in self.fields and v)
        else:  # count only empty values
            return sum(v not in EMPTY_VALUES for key, v in value.items() if key in self.fields)


class AnyOf(RequiredFieldCombinationValidatorBase):
    """Require at least one of fields to be non-empty."""

    def __call__(self, value):
        if self.field_value_count(value) == 0:
            message = _("At least one of fields {} is required.").format(self.msg_fields)
            raise serializers.ValidationError(message)


class OneOf(RequiredFieldCombinationValidatorBase):
    """Require exactly one of fields to be non-empty."""

    def __init__(self, fields, required=False, count_all_falsy=False):
        self.required = required
        super().__init__(fields, count_all_falsy=count_all_falsy)

    def __call__(self, value):
        count = self.field_value_count(value)
        if count == 0 and not self.required:
            return
        if count != 1:
            if self.required:
                message = _("Exactly one of fields {} is required.").format(self.msg_fields)
            else:  # allow 0 or 1
                message = _("Only one of fields {} is allowed.").format(self.msg_fields)
            raise serializers.ValidationError(message)


class AllOf(RequiredFieldCombinationValidatorBase):
    """Require all of listed fields."""

    def __call__(self, value):
        errors = {}
        for field in self.fields:
            if self.count_all_falsy:
                if not value.get(field):
                    errors[field] = _("Field is required.")
            else:
                if value.get(field) in EMPTY_VALUES:
                    errors[field] = _("Field is required.")
        if errors:
            raise serializers.ValidationError(errors)
