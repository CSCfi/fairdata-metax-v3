from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader


class Command(BaseCommand):
    help = "Shows migrations that have been applied but are currently unavailable."

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]

        loader = MigrationLoader(connection)

        existing_migrations = set(loader.disk_migrations.keys())
        applied_migrations = set(loader.applied_migrations.keys())
        missing_applied = applied_migrations - existing_migrations
        missing_list = sorted(missing_applied)

        by_app = {}
        for app, migration in missing_list:
            app_migrations = by_app.setdefault(app, [])
            app_migrations.append(migration)

        for app, app_migrations in by_app.items():
            self.stdout.write(app, self.style.MIGRATE_LABEL)
            for migration in app_migrations:
                self.stdout.write(f"  {migration}")
