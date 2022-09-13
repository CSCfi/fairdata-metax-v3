import os

from django.conf import settings
from django.contrib.auth import get_user_model

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
