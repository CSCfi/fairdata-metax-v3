import csv
import logging

from django import forms
from django.core import exceptions
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import fields, rest_framework as filters

logger = logging.getLogger("__name__")


def parse_csv_string(string):
    reader = csv.reader([string], delimiter=",", quotechar='"', escapechar="\\")
    return next(reader)


def parse_search_string(string):
    reader = csv.reader([string], delimiter=" ", quotechar='"', escapechar="\\")
    return next(reader)


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


class MultipleTextInput(forms.TextInput):
    def value_from_datadict(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get
        return getter(name)


class MultipleCharField(forms.CharField):
    widget = MultipleTextInput

    default_error_messages = {
        "invalid_list": _("Enter a list of values."),
    }

    def to_python(self, value):
        if not value:
            return []
        elif not isinstance(value, (list, tuple)):
            raise forms.ValidationError(self.error_messages["invalid_list"], code="invalid_list")

        return [parse_csv_string(str(val)) for val in value]


class MultipleCharFilter(filters.MultipleChoiceFilter):
    field_class = MultipleCharField

    def filter(self, qs, value):
        if not value:
            # Even though not a noop, no point filtering if empty.
            return qs

        if self.is_noop(qs, value):
            return qs

        qq = Q()
        for term in value:
            q = Q()
            for v in set(term):
                predicate = self.get_filter_predicate(v)
                q |= Q(**predicate)
            qq &= q

        qs = qs.filter(qq)

        return qs.distinct() if self.distinct else qs


class SearchField(forms.CharField):
    def to_python(self, value):
        if not value:
            return []
        if not isinstance(value, (str)):
            raise forms.ValidationError(self.error_messages["invalid_str"], code="invalid_str")

        return parse_search_string(str(value))


class SearchFilter(filters.CharFilter):
    field_class = SearchField


class CustomDjangoFilterBackend(filters.DjangoFilterBackend):
    """Filter backend that shows boolean filters as booleans in swagger."""

    def get_operation_parameter_type(self, field):
        if isinstance(field, filters.BooleanFilter):
            return "boolean"
        return "string"

    def get_schema_operation_parameters(self, view):
        try:
            queryset = view.get_queryset()
        except Exception:
            queryset = None

        filterset_class = self.get_filterset_class(view, queryset)

        if not filterset_class:
            return []

        parameters = []
        for field_name, field in filterset_class.base_filters.items():
            parameter = {
                "name": field_name,
                "required": field.extra["required"],
                "in": "query",
                "description": field.label if field.label is not None else field_name,
                "schema": {
                    # Original implementation always uses "string" type here
                    "type": self.get_operation_parameter_type(field),
                },
            }
            if field.extra and "choices" in field.extra:
                parameter["schema"]["enum"] = [c[0] for c in field.extra["choices"]]
            parameters.append(parameter)
        return parameters
