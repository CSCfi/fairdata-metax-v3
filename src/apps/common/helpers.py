import copy
import logging
import re
import uuid
from contextlib import contextmanager
from datetime import datetime
from textwrap import dedent
from typing import Dict, Optional

from cachalot.api import cachalot_disabled
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django_filters import NumberFilter
from drf_yasg import openapi
from rest_framework.fields import empty

logger = logging.getLogger(__name__)

user_details = {
    "username": settings.METAX_SUPERUSER["username"],
    "email": settings.METAX_SUPERUSER["email"],
    "is_superuser": True,
}


def get_technical_metax_user():
    """Get (or create) technical metax user."""
    obj, created = get_user_model().objects.get_or_create(
        username=user_details["username"], defaults=user_details
    )
    if created is True:
        obj.set_password(settings.METAX_SUPERUSER["password"])
        obj.save()
    return obj.id


def update_or_create_instance(serializer, instance, data):
    if instance is not None:
        serializer.update(instance, data)
        return instance
    else:
        return serializer.create(data)


def parse_iso_dates_in_nested_dict(d: Dict) -> Dict:
    """Recursive function to parse ISO dates to datetime objects in nested dictionaries

    Args:
        d (Dict): Dictionary to parse

    Returns:
        Dict: Parsed dictionary.

    Note:
        The returned dictionary is the same reference as the dictionary in the args."""

    def parse_date_or_datetime(value):
        try:
            return parse_datetime(value)
        except TypeError:
            pass
        try:
            return parse_date(value)
        except TypeError:
            pass
        return None

    for key, value in d.items():
        # If there is nested dictionary, recurse
        if isinstance(value, dict):
            parse_iso_dates_in_nested_dict(value)

        # If there is array in the dictionary, check if it contains dictionary. If not then try to parse the value.
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    parse_iso_dates_in_nested_dict(item)
                else:
                    if date := parse_date_or_datetime(item):
                        value[i] = date
        # If the value is not a dictionary, try to parse it to date
        else:
            try:
                if date := parse_date_or_datetime(value):
                    d[key] = date
            except TypeError:
                pass
    return d


def get_attr_or_item(obj, key):
    """Return value for attribute. If not found, get item with key. Return None if not found."""
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except (KeyError, IndexError, TypeError):
        pass
    return None


@contextmanager
def cachalot_toggle(enabled=True, all_queries: bool = False):
    """Context manager that allows disabling cachalot.

    Useful for heavy one-off queries that may be too large for memcached.

    Usage:
        with cachalot_toggle(enabled=False):
            do_stuff() # run code without caching
    """
    if enabled:
        yield
    else:
        with cachalot_disabled(all_queries=all_queries):
            yield


def get_filter_openapi_parameters(filterset_class):
    """
    Extract OpenAPI (swagger) parameters for filter query parameters.

    Useful in special cases where automatic swagger generation
    is unable to produce query parameters for a view. Most of
    the time (i.e. for 'list' method of a ViewSet that has 'filterset_class')
    the parameters are produced automatically by DjangoFilterBackend.

    Usage example:
    ```
    @swagger_auto_schema(
        manual_parameters=get_filter_openapi_parameters(SomeFilterSet),
    )
    def view_function_to_decorate():
        ...
    ```
    """

    params = []
    for name, field in filterset_class.base_filters.items():
        extra = field.extra or {}
        choices = [c[0] for c in extra.get("choices", [])] or None
        typ = openapi.TYPE_STRING
        if isinstance(field, NumberFilter):
            typ = openapi.TYPE_NUMBER

        description = str(extra.get("help_text", "")) or field.label
        param = openapi.Parameter(
            name=name,
            required=field.extra["required"],
            in_="query",
            description=description,
            type=typ,
            enum=choices,
        )
        params.append(param)
    return params


def prepare_for_copy(obj):
    obj = copy.deepcopy(obj)
    obj.id = None
    obj.pk = None
    obj._state.adding = True
    # Clear prefetch cache to avoid false reverse and m2m relations
    if cache := getattr(obj, "_prefetched_objects_cache", None):
        cache.clear()
    return obj


def ensure_instance_id(instance):
    if not instance.id:
        instance.save()


def date_to_datetime(date):
    """Convert UTC date to datetime."""
    return datetime(year=date.year, month=date.month, day=date.day, tzinfo=timezone.utc)


def datetime_to_date(dt):
    """Convert datetime to UTC date."""
    return dt.astimezone(timezone.utc).date()


def changed_fields(a: dict, b: dict) -> dict:
    all_keys = set(a) | set(b)
    return sorted(key for key in all_keys if a.get(key, empty) != b.get(key, empty))


def is_valid_uuid(val):
    if isinstance(val, uuid.UUID):
        return True
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def deduplicate_list(lst: list):
    """Deduplicate list of hashable items."""
    added = {}
    return [added.setdefault(item, item) for item in lst if item not in added]


def has_values(obj: dict, exclude=None):
    if exclude is None:
        exclude = set()
    return any({1 for key, value in obj.items() if key not in exclude})


def format_multiline(string: str, *args, **kwargs) -> str:
    """Multiline string cleanup and formatting helper.

    Does the following:
    - Remove leading and trailing newlines
    - Remove all whitespace after "\\" (so it can be used for line continuation)
    - Remove common indentation
    - Format string with `.format` using the provided"" arguments.
    """
    string = string.strip("\n")
    string = re.sub("\\\\\s+", "", string)
    return dedent(string).format(*args, **kwargs)


def single_translation(value: dict) -> Optional[str]:
    """Return single translation value for multilanguage dict."""
    if not value:
        return value

    order = ["en", "fi", "sv", "und"]
    for lang in order:
        if translation := value.get(lang):
            return translation

    # Return first value
    return next(iter(value.values()), None)


def omit_none(value: dict) -> dict:
    """Return copy of dict with None values removed."""
    return {key: val for key, val in value.items() if val is not None}
