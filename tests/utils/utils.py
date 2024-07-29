from collections import OrderedDict

from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import exceptions, fields


def _values_eql(a, b):
    """Test value equality.

    Returns True if
    * values are equal
    * one of the values is a DRF Field that the other value successfully validates as
    * values are strings that represent the same date or datetime."""
    if a == b:
        return True
    try:
        if isinstance(a, fields.Field):
            a.run_validation(data=b)
            return True
        if isinstance(b, fields.Field):
            b.run_validation(data=a)
            return True
    except exceptions.ValidationError:
        return False
    if isinstance(a, str) and isinstance(b, str):
        dt_a = parse_date(a) or parse_datetime(a)
        dt_b = parse_date(b) or parse_datetime(b)
        if dt_a and dt_b:
            return dt_a == dt_b
    return False


def assert_nested_subdict(
    sub: dict, full: dict, check_all_keys_equal=False, check_list_length=False
):
    """Assert that all key-value pairs in dict are contained by another dict.

    Arguments:
    * sub: dictionary that should be a subset of `full`
    * full: dictionary that contains all key-value pairs of `sub`
    * check_all_keys_equal: If enabled, values in `full` but not in `sub` fail test.
    * check_list_length: If enabled, check that lists are equal length."""

    def recurse(sub_value, full_value, path):
        # convert OrderedDict to dict
        if isinstance(sub_value, OrderedDict):
            sub_value = dict(sub_value)
        if isinstance(full_value, OrderedDict):
            full_value = dict(full_value)

        # convert lists to dicts
        is_list = False
        if isinstance(sub_value, list) and isinstance(full_value, list):
            is_list = True
            if check_list_length and len(sub_value) != len(full_value):
                raise AssertionError(
                    f"Lists have different lengths, {path}: {len(sub_value)} != {len(full_value)}"
                )
            sub_value = dict(enumerate(sub_value))
            full_value = dict(enumerate(full_value))

        # if either is non-dict, check equality and return
        if not (isinstance(sub_value, dict) and isinstance(full_value, dict)):
            if not _values_eql(full_value, sub_value):
                raise AssertionError(f"Different values for {path}: {sub_value} != {full_value}")
            return

        # both are dicts, check keys and recurse
        if check_all_keys_equal and not is_list:
            missing_from_sub = set(full_value) - set(sub_value)
            if len(missing_from_sub) > 0:
                raise AssertionError(f"Keys missing from sub dict: {', '.join(missing_from_sub)}")

        for key, inner_sub_value in sub_value.items():
            key_path = f"{path}.{key}" if path else key
            if key not in full_value:
                raise AssertionError(f"Value missing from full dict: {key_path}={inner_sub_value}")
            inner_full_value = full_value[key]
            recurse(
                sub_value=inner_sub_value,
                full_value=inner_full_value,
                path=key_path,
            )

    recurse(sub, full, path="")
