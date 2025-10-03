import copy
import logging
import pickle
import re
import uuid
import sys
import traceback
from collections.abc import Hashable
from contextlib import contextmanager
from datetime import datetime, timezone as tz
from itertools import islice
from textwrap import dedent
from typing import Dict, Iterable, List, Optional
from urllib.parse import SplitResult, parse_qsl, quote, urlencode, urlsplit, urlunsplit

import shapely
from cachalot.api import cachalot_disabled
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.dateparse import parse_date, parse_datetime
from django_filters import NumberFilter
from drf_yasg import openapi
from rest_framework import serializers
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


def parse_date_or_datetime(value):
    try:
        # Depending on error, parse_datetime may return None or raise TypeError
        if dt := parse_datetime(value):
            return dt.astimezone(tz.utc)
    except TypeError:
        pass

    try:
        return parse_date(value)
    except TypeError:
        pass
    return None


def parse_iso_dates_in_nested_dict(d: Dict) -> Dict:
    """Recursive function to parse ISO dates to datetime objects in nested dictionaries.

    Args:
        d (Dict): Dictionary to parse

    Returns:
        Dict: Parsed dictionary.

    Note: The dictionary values are updated in-place."""
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
            if date := parse_date_or_datetime(value):
                d[key] = date
    return d


def process_nested(value, pre_handler=None, post_handler=None, path=""):
    """Generic nested dict and list processing.

    For each nested value:
    - Pass value through pre_handler callback
    - In case of dict or list, copy it and process contained values
    - Pass value through post_handler callback
    """
    if pre_handler:
        value = pre_handler(value, path)
    if isinstance(value, dict):
        value = {
            k: process_nested(v, pre_handler, post_handler, path=path + f".{k}")
            for k, v in value.items()
        }
    elif isinstance(value, list):
        value = [
            process_nested(v, pre_handler, post_handler, path=path + f"[{i}]")
            for i, v in enumerate(value)
        ]
    if post_handler:
        value = post_handler(value, path)
    return value


def get_attr_or_item(obj, key, default=empty):
    """Return value for attribute. If not found, get item with key.

    Raises an error if no value is not found and no default is set.
    """
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except (KeyError, IndexError, TypeError):
        if default is empty:
            raise
    return default


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


def prepare_for_copy(obj: models.Model, create_new_id=True) -> models.Model:
    obj = copy.deepcopy(obj)
    new_id = None
    if create_new_id:
        new_id = obj._meta.get_field("id").get_default()
    obj.id = new_id
    obj.pk = new_id

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
    return datetime(year=date.year, month=date.month, day=date.day, tzinfo=tz.utc)


def datetime_to_date(dt):
    """Convert datetime to UTC date."""
    if dt is None:
        return None
    return dt.astimezone(tz.utc).date()


def changed_fields(a: dict, b: dict) -> list:
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


def is_valid_float_str(val):
    try:
        float(val)
        return True
    except ValueError:
        return False


def is_valid_url(val):
    try:
        serializers.URLField().run_validation(val)
    except serializers.ValidationError:
        return False
    return True


def is_valid_email(val):
    try:
        serializers.EmailField().run_validation(val)
    except serializers.ValidationError:
        return False
    return True


# Special characters that don't require percent encoding
# See https://datatracker.ietf.org/doc/html/rfc3986#section-3.3
safe_pchar = r"!$&'()*+,;=:@"
safe_fragment = safe_pchar + r"/?"


def quote_url(url: str) -> str:
    """Percent-encode url. Assumes any '%' characters in the url are already correct.

    Note: Empty URL components (e.g. '#' in 'https://example.com#')
    are removed from the resulting URL due to how urllib works.
    See https://github.com/python/cpython/issues/67041
    """
    parts = urlsplit(url)
    quoted_parts = SplitResult(
        scheme=parts.scheme,
        netloc=parts.netloc,
        path=quote(parts.path, safe=safe_pchar + "/%"),
        query=urlencode(parse_qsl(parts.query), safe=safe_fragment + "%"),
        fragment=quote(parts.fragment, safe=safe_fragment + "%"),
    )
    return urlunsplit(quoted_parts)


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
    string = re.sub(r"\\\s+", "", string)
    return dedent(string).format(*args, **kwargs)


def single_translation(value: dict, preferred_lang=None) -> Optional[str]:
    """Return single translation value for multilanguage dict."""
    if not value:
        return value

    order = ["en", "fi", "sv", "und"]
    if preferred_lang:
        order = [preferred_lang, *order]
    for lang in order:
        if translation := value.get(lang):
            return translation

    # Return first value
    return next(iter(value.values()), None)


def omit_none(value: dict) -> dict:
    """Return copy of dict with None values removed."""
    return {key: val for key, val in value.items() if val is not None}


def is_empty_string(value: str) -> str:
    return type(value) is str and value.strip() == ""


def omit_empty(value: dict, recurse=False) -> dict:
    """Return copy of dict with None values and empty lists, empty strings and empty dicts removed."""
    if not recurse:
        return {
            key: val
            for key, val in value.items()
            if val not in [None, "", {}, []] and not is_empty_string(val)
        }

    def _recurse(_value):
        if isinstance(_value, list):
            return [
                _val
                for val in _value
                if (_val := _recurse(val)) not in [None, "", {}, []] and not is_empty_string(_val)
            ]

        if isinstance(_value, dict):
            return {
                key: _val
                for key, val in _value.items()
                if (_val := _recurse(val)) not in [None, "", {}, []] and not is_empty_string(_val)
            }
        return _value

    return _recurse(value)


def ensure_list(lst) -> list:
    """Convert None into empty list, raise validation error on other non-list values."""
    if lst is None:
        return []
    if not isinstance(lst, list):
        raise serializers.ValidationError(f"Value is not a list: {lst}")
    return lst


def ensure_dict(dct) -> dict:
    """Raise validation error on non-dict values values."""
    if not isinstance(dct, dict):
        raise serializers.ValidationError(f"Value is not a dict: {dct}")
    return dct


def remove_wkt_point_duplicates(point: str, wkt_list: list) -> list:
    """Remove points from `wkt_list` that are equal or very similar to `point`.

    Keeps invalid wkt data intact.
    """
    output = []
    p1 = shapely.wkt.loads(point)
    for p2_wkt in wkt_list:
        try:
            p2 = shapely.wkt.loads(p2_wkt)
            if p2.geom_type == "Point" and p1.distance(p2) < 0.0001:
                continue
        except shapely.errors.GEOSException:
            pass
        output.append(p2_wkt)
    return output


def is_field_value_provided(model, field_name: str, args: list, kwargs: dict):
    """Determine if Model.__init__ arguments have a value for field_name.

    Useful when we require a default value that is different from the field default.
    """
    # Is value provided in kwargs?
    if field_name in kwargs:
        return True

    # Is value provided in args?
    index = None
    for index, field in enumerate(model._meta.concrete_fields):
        if field.attname == field_name:
            return len(args) > index

    # Field does not exist in model
    raise ValueError(f"Concrete model field not found: {model.__name__}.{field_name}")


def batched(iterable, n):
    """Implementation of itertools.batched upcoming in Python 12.

    See https://docs.python.org/3/library/itertools.html#itertools.batched
    """
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def datetime_to_header(dt: datetime):
    """Convert datetime into format used by e.g. If-Modified-Since HTTP header."""
    return dt.astimezone(tz.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def merge_sets(sets: List[Iterable[Hashable]]) -> List[set]:
    """Merge all sets that contain at least one common element."""
    supersets = []
    superset_by_value = {}
    for current_set in sets:
        # Find if a value in set is already in a superset
        superset = None
        for value in current_set:
            if existing_superset := superset_by_value.get(value):
                if superset is None:
                    superset = existing_superset
                elif existing_superset is not superset:
                    # Set has values from multiple supersets,
                    # move all values from other supersets to current
                    superset.update(existing_superset)
                    for other_value in existing_superset:
                        superset_by_value[other_value] = superset
                    existing_superset.clear()

        # No superset found, create new
        if not superset:
            superset = set()
            supersets.append(superset)

        superset.update(current_set)
        for value in current_set:
            superset_by_value[value] = superset

    # Return non-empty sets
    return [s for s in supersets if len(s) > 0]


def pickle_deepcopy(value):
    """Deep copy value using pickle. Faster than copy.deepcopy()."""
    return pickle.loads(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


doi_re = re.compile(r"(https://doi.org/|http://doi.org/|doi:)?(?P<identifier>10\..*)")


def normalize_doi(identifier: str) -> Optional[str]:
    """If identifier looks like it could be a DOI, return it in "doi:..." format."""
    if match := doi_re.match(identifier):
        return f"doi:{match.group('identifier')}"
    return None


def format_exception(exception: BaseException) -> str:
    """Format exception as a string."""
    # Use new format_exception signature for python >= 3.10
    if sys.version_info >= (3, 10):
        return "".join(traceback.format_exception(exception))

    return "".join(
        traceback.format_exception(
            etype=type(exception), value=exception, tb=exception.__traceback__
        )
    )


def datetime_fromisoformat(str) -> datetime:
    """Parse datetime from string in ISO 8601 format."""
    if sys.version_info >= (3, 11):
        return datetime.fromisoformat(str)

    # Python < 3.11 needs to use external library because that version
    # of datetime.fromisoformat doesn't yet support the formats we use
    import isodate
    return isodate.parse_datetime(str)
