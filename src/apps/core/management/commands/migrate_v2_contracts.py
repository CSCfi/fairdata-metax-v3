import logging
from argparse import ArgumentParser

from cachalot.api import cachalot_disabled
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models.contract import Contract

from ._v2_client import MigrationV2Client

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Migrate V2 contracts to V3 from specific Metax instance

    Examples:
        Migrate all contracts from configured metax instance

            $ python manage.py migrate_v2_contracts --use-env
    """

    allow_fail = False
    created = 0
    updated = 0
    migrated = 0
    ok_after_update = 0
    migration_limit = 0
    compatibility_errors = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metax_instance = None
        self.metax_user = None
        self.metax_password = None

    def add_arguments(self, parser: ArgumentParser):
        MigrationV2Client.add_arguments(parser)
        parser.add_argument(
            "--pagination-size",
            "-ps",
            type=int,
            required=False,
            default=1000,
            help="Number of storages to migrate per request",
        )
        parser.add_argument(
            "--allow-fail",
            "-af",
            action="store_true",
            required=False,
            default=False,
            help="Allow individual datasets to fail without halting the migration",
        )

    def print_status_line(self, identifier):
        created = self.created
        updated = self.updated
        processed = self.migrated
        self.stdout.write(f"{processed=}, {created=:}, {updated=:}, {identifier=}")

    def migrate_all_contracts(self, params):
        self.stdout.write("--- Migrating all contracts ---")
        legacy_contracts = self.client.fetch_contracts(params)
        for legacy_contract in legacy_contracts:
            try:
                contract, created = Contract.create_or_update_from_legacy(legacy_contract)
                if created:
                    self.created += 1
                else:
                    self.updated += 1
            except Exception as e:
                if self.allow_fail:
                    self.stderr.write(f"Error processing contract: {e}")
                else:
                    raise
            self.print_status_line(contract.contract_identifier)

    def migrate_from_metax(self, options):
        self.allow_fail = options.get("allow_fail")
        limit = options.get("pagination_size")
        params = {"limit": limit}
        self.migrate_all_contracts(params)

    def handle(self, *args, **options):
        self.started = timezone.now()
        self.allow_fail = options.get("allow_fail")
        self.verbosity = options.get("verbosity")  # defaults to 1

        self.client = MigrationV2Client(options, stdout=self.stdout, stderr=self.stderr)
        if not self.client.ok:
            self.stderr.write("Missing Metax V2 configuration")
            return

        try:
            with cachalot_disabled():
                self.migrate_from_metax(options)
        except KeyboardInterrupt:
            pass
