from django.utils.dateparse import parse_datetime, parse_date
from collections import OrderedDict


def values_eql(a, b):
    """Test if values are equal or are strings that represent the same date or datetime."""
    if a == b:
        return True
    if type(a) == str and type(b) == str:
        dt_a = parse_date(a) or parse_datetime(a)
        dt_b = parse_date(b) or parse_datetime(b)
        if dt_a and dt_b:
            return dt_a == dt_b
    return False


def assert_nested_subdict(sub: dict, full: dict, path=""):
    """Assert that all values in dict `sub` are contained by `full`.

    Values in `full` but not in `sub` are ignored."""
    for key, sub_value in sub.items():
        key_path = f"{path}.{key}" if path else key
        if key not in full:
            raise AssertionError(f"Value missing from dict: {key_path}={sub_value}")
        full_value = full[key]
        if isinstance(sub_value, OrderedDict):
            sub_value = dict(sub_value)
        if isinstance(full_value, OrderedDict):
            full_value = dict(full_value)

        # convert lists to dicts
        if isinstance(sub_value, list) and isinstance(full_value, list):
            sub_value = dict(enumerate(sub_value))
            full_value = dict(enumerate(full_value))

        if isinstance(sub_value, dict) and isinstance(full_value, dict):
            assert_nested_subdict(sub_value, full_value, path=key_path)
        elif not values_eql(full_value, sub_value):
            raise AssertionError(
                f"Dicts have different values for {key_path}: {sub_value} != {full_value}"
            )
