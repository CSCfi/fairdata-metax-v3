import logging

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Create or update appsupport group with view access to most models in admin."""

    excluded_permissions = ["view_authtoken", "view_token"]

    def handle(self, *args, **options):
        with transaction.atomic():
            view_permissions = Permission.objects.filter(codename__startswith="view_").exclude(
                codename__in=self.excluded_permissions
            )
            group, _created = Group.objects.get_or_create(name="appsupport")
            group.permissions.set(view_permissions)
