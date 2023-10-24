# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging
from collections import OrderedDict

import shapely.wkt
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import empty, to_choices_dict
from rest_framework.utils import html

from apps.common.models import MediaTypeValidator

logger = logging.getLogger(__name__)


def check_child_model_serializer(child):
    assert isinstance(
        child, serializers.ModelSerializer
    ), "The `child` argument should be a model serializer."

    assert "url" in child.fields, "The `child` serializer should have a `url` field."


class URLReferencedModelListField(serializers.ListField):
    """Custom field for a model list.

    Allows user to represent targets using the 'url' key.

    The 'child' parameter in 'serializers.ListField' is used for serializing
    the list in the response.
    """

    def __init__(self, **kwargs):
        check_child_model_serializer(kwargs.get("child"))
        super().__init__(**kwargs)

    def to_representation(self, manager):
        if isinstance(manager, list):
            return [self.child.to_representation(entry) for entry in manager]
        else:
            return [self.child.to_representation(entry) for entry in manager.all()]

    def to_internal_value(self, data):
        if not isinstance(data, list) or isinstance(data, (str, dict)):
            self.fail("not_a_list", input_type=type(data).__name__)

        if data and hasattr(data[0], "url"):
            # The list of entries has already been converted into model
            # instances
            return data

        try:
            urls = set(entry["url"] for entry in data)
        except KeyError:
            raise serializers.ValidationError(
                "'url' field must be defined for each object in the list"
            )
        except TypeError:
            raise serializers.ValidationError(
                "Each item in the list must be an object with the field 'url'"
            )

        model = self.child.Meta.model
        entries = list(model.objects.filter(url__in=urls))

        retrieved_urls = set(entry.url for entry in entries)
        missing_urls = urls - retrieved_urls

        if missing_urls:
            raise serializers.ValidationError(
                "Entries not found for given URLs: {}".format(", ".join(missing_urls))
            )

        return entries


class URLReferencedModelField(serializers.RelatedField):
    """Serialized RelatedField for URL-referenced concepts.

    Accepts input data in the format
    {
        "url": ...
    }
    which is then used to fetch a model instance.
    The instance is serialized using a model serializer.
    The serializer is expected to have a "url" field.

    The field is essentially a wrapper around a concept serializer.
    Using a non-serializer field here prevents the parent serializer
    from complaining about unsupported writable nested serializers.
    """

    default_error_messages = {
        "does_not_exist": _("Entry not found for url '{url_value}'."),
    }

    def __init__(self, child: serializers.ModelSerializer, **kwargs):
        check_child_model_serializer(child)
        self.queryset = child.Meta.model.objects.all()
        self.child = child
        # Always allow child to be null. Otherwise both parent and child would require allow_null,
        # e.g. `URLReferencedModelField(Child(allow_null=True), allow_null=True)`
        child.allow_null = True
        self.child.bind(field_name="", parent=self)
        super().__init__(**kwargs)

    @classmethod
    def many_init(cls, **kwargs):
        """For many=True use custom list field that retrieves multiple urls at once."""
        return URLReferencedModelListField(**kwargs)

    def run_validation(self, data=empty):
        try:
            if data is not empty:
                data = self.child.run_validation(data)
            return serializers.Field.run_validation(self, data)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError(exc.detail)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(url=data["url"])
        except ObjectDoesNotExist:
            self.fail("does_not_exist", url_value=data["url"])

    def to_representation(self, value):
        return self.child.to_representation(value)

    def get_value(self, dictionary):
        """Convert DRF forms input from json to dict."""
        value = super().get_value(dictionary)
        if html.is_html_input(dictionary):
            value = json.loads(value)
        return value

    def get_choices(self, cutoff=None):
        """Modified get_choices that converts dict to json for DRF forms."""
        queryset = self.get_queryset()
        if queryset is None:
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict(
            [
                (json.dumps(self.to_representation(item)), self.display_value(item))
                for item in queryset
            ]
        )


class ChecksumField(serializers.RegexField):
    allowed_algorithms = ["md5", "sha256", "sha512"]
    checksum_regex = rf"^({'|'.join(allowed_algorithms)}):[a-z0-9_]+$"

    default_error_messages = {
        "invalid": _(
            "Checksum should be a lowercase string in format 'algorithm:value'. "
            "Allowed algorithms are: {}."
        ).format(allowed_algorithms)
    }

    def __init__(self, *args, **kwargs):
        kwargs["trim_whitespace"] = False
        super().__init__(self.checksum_regex, *args, **kwargs)


class ListValidChoicesField(serializers.ChoiceField):
    """ChoiceField that lists valid choices in the 'invalid choice' error message."""

    def __init__(self, *args, **kwargs):
        choices = kwargs.get("choices", [])
        kwargs["error_messages"] = {
            "invalid_choice": serializers.ChoiceField.default_error_messages["invalid_choice"]
            + " "
            + _("Valid choices are: {choices}").format(
                choices=[c for c in to_choices_dict(choices)]
            ),
            **kwargs.get("error_messages", {}),
        }

        super().__init__(*args, **kwargs)


class MediaTypeField(serializers.CharField):
    default_error_messages = {"invalid": _("Value should contain a media type, e.g. 'text/csv'.")}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        validator = MediaTypeValidator(message=self.error_messages["invalid"])
        self.validators.append(validator)


class WKTField(serializers.CharField):
    """Serializer field that accepts a WKT string and normalizes it."""

    def to_internal_value(self, data):
        try:
            return shapely.wkt.loads(data).wkt
        except shapely.errors.GEOSException as error:
            raise serializers.ValidationError(_("Invalid WKT: {}").format(str(error)))
