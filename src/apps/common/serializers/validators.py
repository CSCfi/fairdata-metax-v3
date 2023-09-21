from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class RequiredFieldCombinationValidatorBase:
    def __init__(self, fields):
        self.fields = set(fields)

    @property
    def msg_fields(self):
        return ", ".join(f"'{f}'" for f in sorted(self.fields))

    def field_value_count(self, value):
        """Count how many non-empty field values exist."""
        return sum(v not in EMPTY_VALUES for key, v in value.items() if key in self.fields)


class AnyOf(RequiredFieldCombinationValidatorBase):
    """Require at least one of fields to be non-empty."""

    def __call__(self, value):
        if self.field_value_count(value) == 0:
            message = _("At least one of fields {} is required.").format(self.msg_fields)
            raise serializers.ValidationError(message)
