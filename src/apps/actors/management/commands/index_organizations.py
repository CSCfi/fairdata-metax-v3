from django.core.management.base import BaseCommand

from apps.actors.services.organization_indexer import OrganizationIndexer
from django.conf import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        indexer = OrganizationIndexer()
        indexer.index()
