import logging
import os
from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "--groups",
            "-g",
            nargs="+",
            type=str,
            help="List of groups to add user to",
        )
        parser.add_argument(
            "--token-override",
            action="store_true",
            required=False,
            default=False,
            help="Override authentication token with value from AUTH_TOKEN_VALUE env-var",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            User = get_user_model()
            user, created = User.objects.get_or_create(username=options["username"])
            groups = options.get("groups")
            token_override = options.get("token_override")

            if groups:
                user.groups.clear()
                for group in groups:
                    obj, created = Group.objects.get_or_create(name=group)
                    user.groups.add(obj)
            if token_override:
                Token.objects.filter(user=user).delete()
                token_value = os.environ.get("AUTH_TOKEN_VALUE")
                Token.objects.create(user=user, key=token_value)
