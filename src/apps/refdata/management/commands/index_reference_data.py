from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.refdata.services import indexer


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_choices = [*settings.REFERENCE_DATA_SOURCES.keys()]

    def add_arguments(self, parser):
        parser.add_argument(
            "types",
            nargs="*",
            help=f"List of reference data types to index. If omitted, index all types. Available: {self.type_choices}",
        )

    def handle(self, *args, **options):
        types = options["types"] or self.type_choices

        if len(types) != len(set(types)):
            raise CommandError("Duplicate arguments supplied")

        unknown = set(types) - set(self.type_choices)
        if len(unknown) != 0:
            raise CommandError(f"Unknown types: {sorted(unknown)}, available: {self.type_choices}")

        return indexer.index(types=types)
