import logging
from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Create staff user belonging to the appsupport group.

    Users will be able to login to the admin UI where
    they have read-only access to most models.

    Also runs create_appsupport_group to ensure the appsupport
    group exists and is up to date.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("username", type=str)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--email", type=str, required=False)

    def handle(self, *args, **options):
        with transaction.atomic():
            call_command("create_appsupport_group")
            user_model = get_user_model()
            user, _created = user_model.objects.get_or_create(username=options["username"])
            user.is_staff = True
            user.set_password(options["password"])
            user.email = options.get("email")
            user.save()

            groups = [Group.objects.get(name="appsupport")]
            user.groups.set(groups)
