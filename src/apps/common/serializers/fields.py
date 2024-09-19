# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json
import logging
from collections import OrderedDict
from typing import Mapping

import shapely.wkt
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
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
            model_name = self.child.Meta.model.__name__
            raise serializers.ValidationError(
                "{model_name} entries not found for given URLs: {urls}".format(
                    model_name=model_name, urls=", ".join(missing_urls)
                )
            )

        return entries


class ReferenceDataCache:
    """Helper class for caching reference data in serializer context."""

    notfound = object()  # Notfound in cache indicates object does not exist

    def __init__(self, model):
        self.model = model
        self.entries = {}

    @classmethod
    def from_context(cls, context: dict, model):
        caches = context.setdefault("refdata_caches", {})
        model_name = model.__name__
        cache = caches.get(model_name)
        if not cache:
            # Create new cache for model
            cache = cls(model)
            caches[model_name] = cache
        return cache

    def add_url(self, url):
        """Add url to entries."""
        self.entries.setdefault(url, None)  # Entry is None if queried yet

    def get(self, url):
        """Get entry from cache or query entry from DB."""
        self.add_url(url)
        val = self.entries[url]
        if val is None:
            # Entry not queried yet, query all entries that haven't been queried yet
            instances = self.model.available_objects.filter(
                url__in=[_url for _url, entry in self.entries.items() if entry is None]
            )
            self.entries.update({entry.url: entry for entry in instances})

            # If entry with url wasn't found, mark it as not found
            for _url, entry in self.entries.items():
                if entry is None:
                    self.entries[_url] = self.notfound
            val = self.entries[url]
        if val is self.notfound:
            raise self.model.DoesNotExist()
        return val


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
        "does_not_exist": _("{model_name} entry not found for url '{url_value}'."),
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

    def preprocess(self, data):
        """Collect urls in a "refdata" dict in context."""
        if isinstance(data, Mapping):
            if url := data.get("url"):
                cache = ReferenceDataCache.from_context(
                    context=self.context, model=self.child.Meta.model
                )
                cache.add_url(url)

    def to_internal_value(self, data):
        try:
            cache = ReferenceDataCache.from_context(
                context=self.context, model=self.child.Meta.model
            )
            return cache.get(data["url"])
        except ObjectDoesNotExist:
            model_name = self.child.Meta.model.__name__
            self.fail("does_not_exist", url_value=data["url"], model_name=model_name)

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


class ChecksumField(serializers.CharField):
    allowed_algorithms = ["md5", "sha256", "sha512"]

    default_error_messages = {
        "invalid": _(
            "Checksum should be a lowercase string in format 'algorithm:value'. "
            "Allowed algorithms are: {allowed_algorithms}."
        )
    }

    @property
    def checksum_regex(self):
        return rf"^({'|'.join(self.allowed_algorithms)}):[a-z0-9_]+$"

    def fail(self, key, **kwargs):
        kwargs["allowed_algorithms"] = self.allowed_algorithms
        return super().fail(key, **kwargs)

    def __init__(self, **kwargs):
        kwargs["trim_whitespace"] = True
        super().__init__(**kwargs)
        validator = RegexValidator(
            self.checksum_regex,
            message=self.error_messages["invalid"].format(
                allowed_algorithms=self.allowed_algorithms
            ),
        )
        self.validators.append(validator)


class RemoteResourceChecksumField(ChecksumField):
    allowed_algorithms = ChecksumField.allowed_algorithms + ["sha1", "sha224", "sha384", "other"]


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


class MultiLanguageField(serializers.HStoreField):
    """Serializer field for MultiLanguageField model fields.

    Languages with `null` or "" as translation are removed from the object.
    Disallows empty objects `{}` by default.
    """

    child = serializers.CharField(allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {
                lang: translation
                for lang, translation in data.items()
                if translation not in [None, ""]
            }
        if data == {} and self.allow_null and not self.allow_empty:
            return None
        return super().to_internal_value(data)

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_empty", False)
        super().__init__(**kwargs)


class NullableCharField(serializers.CharField):
    """CharField that converts empty strings to nulls if allowed."""

    def run_validation(self, data):
        # CharField checks for empty string in run_validation
        # instead of to_internal_value.
        if self.allow_null:
            is_empty = data == "" or (self.trim_whitespace and str(data).strip() == "")
            if is_empty:
                data = None
        return super().run_validation(data)


class PrivateEmailValue:
    """Value container for email addresses.

    Can be cached. Intentionally not JSON serializable by default
    to reduce chance of accidentally leaking values. Needs
    to be removed or converted into string before rendering.
    """

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, value: object) -> bool:
        if isinstance(value, PrivateEmailValue):
            return self.value == value.value
        elif isinstance(value, str):
            return self.value == value
        return super().__eq__(value)

    def __str__(self) -> str:
        return "<PrivateEmailValue>"


def handle_private_emails(value: dict, show_emails, ignore_fields=set()):
    """Convert PrivateEmailValues into strings or hide them recursively."""
    omit = object()

    def recurse(value):
        if isinstance(value, dict):
            for k in list(value.keys()):
                ret = recurse(value[k])
                if ret is not None:
                    if ret is omit:
                        del value[k]
                    else:
                        value[k] = ret
            return None
        if isinstance(value, list):
            for v in value:
                recurse(v)
            return None
        if isinstance(value, PrivateEmailValue):
            return value.value if show_emails else omit

    for k in list(value.keys()):
        if k not in ignore_fields:
            ret = recurse(value[k])
            if ret is not None:
                if ret is omit:
                    del value[k]
                else:
                    value[k] = ret


class PrivateEmailField(serializers.EmailField):
    """Email field that is hidden by CommonModelSerializer by default."""

    def to_representation(self, value):
        self.context["has_emails"] = True
        return PrivateEmailValue(super().to_representation(value))


class ConstantField(serializers.Field):
    """Read-only field that always returns constant value."""

    def __init__(self, value, *args, **kwargs):
        self._value = value
        kwargs["read_only"] = True
        kwargs["default"] = value
        super().__init__(*args, **kwargs)

    def get_attribute(self, instance):
        return self._value

    def to_representation(self, value):
        return value


class CommaSeparatedListField(serializers.ListField):
    """ListField that serializes into a comma-separated string."""

    def get_value(self, dictionary):
        return super(serializers.ListField, self).get_value(dictionary)

    def to_internal_value(self, data):
        data = data.split(",")
        return super().to_internal_value(data)

    def to_representation(self, data):
        return ",".join(data)
