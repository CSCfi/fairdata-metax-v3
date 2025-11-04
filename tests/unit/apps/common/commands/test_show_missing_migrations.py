import pytest
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from io import StringIO


@pytest.mark.django_db
def test_show_missing_migrations():
    applied_migrations = {  # All applied migrations
        ("app1", "0001_initial"),
        ("app1", "0002_auto"),
        ("app2", "0001_initial"),
    }
    disk_migrations = {  # Migrations that exist in installed apps
        ("app1", "0001_initial"),
        ("app2", "0001_initial"),
    }

    # Mock MigrationLoader for the test.
    # Django imports command without "apps." so we need to omit "apps." when patching
    with patch("common.management.commands.show_missing_migrations.MigrationLoader") as MockLoader:
        mock_loader_instance = MagicMock()
        mock_loader_instance.applied_migrations = dict.fromkeys(applied_migrations, None)
        mock_loader_instance.disk_migrations = dict.fromkeys(disk_migrations, None)
        MockLoader.return_value = mock_loader_instance

        # Capture output
        out = StringIO()
        call_command("show_missing_migrations", stdout=out)

        output = out.getvalue()
        assert "app1" in output
        assert "0002_auto" in output
        assert "app2" not in output  # All applied migrations for app2 are present on disk
