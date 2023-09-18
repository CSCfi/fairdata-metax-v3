from django.core import exceptions
from django.utils.translation import gettext_lazy as _
from django_filters import fields, rest_framework as filters
from django import forms


class VerboseChoiceField(fields.ChoiceField):
    default_error_messages = {
        "invalid_choice": _("Value '%(value)s' is not a valid choice.")
        + " "
        + _("Valid choices are: %(choices)s"),
    }

    def validate(self, value):
        """Validate that the input is in self.choices."""
        super(forms.ChoiceField, self).validate(value)
        if value and not self.valid_value(value):
            # Like forms.ChoiceField.validate but adds choices to error params
            raise exceptions.ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value, "choices": list([c[0] for c in self.choices])},
            )


class VerboseChoiceFilter(filters.ChoiceFilter):
    field_class = VerboseChoiceField
