from argparse import ArgumentParser
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.actors.services.organization_indexer import OrganizationIndexer


class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--cached",
            "-c",
            action="store_true",
            required=False,
            default=False,
            help="Use cached organizations from organizations.csv.",
        )

    def handle(self, *args, **options):
        indexer = OrganizationIndexer()
        indexer.index(cached=options.get("cached"))
