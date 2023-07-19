import logging
from typing import Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

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
        new_serializer = serializer.__class__(data=data)
        if new_serializer.is_valid(raise_exception=True):
            return new_serializer


def parse_iso_dates_in_nested_dict(d: Dict) -> Dict:
    """Recursive function to parse ISO dates to datetime objects in nested dictionaries

    Args:
        d (Dict): Dictionary to parse

    Returns:
        Dict: Parsed dictionary.

    Note:
        The returned dictionary is the same reference as the dictionary in the args."""

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
                    try:
                        if date := parse_datetime(item):
                            value[i] = date
                    except TypeError:
                        pass
        # If the value is not a dictionary, try to parse it to date
        else:
            try:
                if date := parse_datetime(value):
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
