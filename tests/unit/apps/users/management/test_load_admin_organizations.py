import json
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.users.models import AdminOrganization

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


@pytest.fixture
def mock_json_data():
    """Mock JSON data for admin organizations."""
    return [
        {
            "id": "test-org-1.fi",
            "pref_label": {
                "fi": "Test Organisaatio 1",
                "en": "Test Organization 1",
            },
        },
        {
            "id": "test-org-2.fi",
            "pref_label": {
                "fi": "Test Organisaatio 2",
                "en": "Test Organization 2",
            },
        },
    ]


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_creates_new_organizations(mock_file, mock_json_load, mock_json_data):
    """Test that the command creates new admin organizations from JSON."""
    # Mock json.load to return our test data
    mock_json_load.return_value = mock_json_data

    # Ensure no organizations exist initially
    assert AdminOrganization.objects.count() == 0

    call_command("load_admin_organizations")

    # Verify organizations were created
    assert AdminOrganization.objects.count() == 2
    assert len(AdminOrganization.objects.all()) == 2

    org1 = AdminOrganization.objects.get(id="test-org-1.fi")
    assert org1.pref_label == {"fi": "Test Organisaatio 1", "en": "Test Organization 1"}

    org2 = AdminOrganization.objects.get(id="test-org-2.fi")
    assert org2.pref_label == {"fi": "Test Organisaatio 2", "en": "Test Organization 2"}

    # Verify file was opened with correct path
    mock_file.assert_called_once_with(
        "src/apps/users/management/initial_data/admin_organizations.json",
        "r",
    )

    # Verify json.load was called
    mock_json_load.assert_called_once()


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_updates_existing_organizations(mock_file, mock_json_load, mock_json_data):
    """Test that the command updates existing admin organizations."""
    # Create an existing organization
    existing_org = AdminOrganization.objects.create(
        id="test-org-1.fi",
        pref_label={"fi": "Vanha nimi", "en": "Old name"},
    )

    # Mock json.load to return our test data
    mock_json_load.return_value = mock_json_data

    call_command("load_admin_organizations")

    # Verify organization count (should still be 2, one updated, one created)
    assert AdminOrganization.objects.count() == 2
    assert len(AdminOrganization.objects.all()) == 2

    # Verify the existing organization was updated with new pref_label
    existing_org.refresh_from_db()
    assert existing_org.pref_label == {"fi": "Test Organisaatio 1", "en": "Test Organization 1"}


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_with_empty_json(mock_file, mock_json_load):
    """Test that the command handles empty JSON array."""
    # Mock empty JSON array
    mock_json_load.return_value = []

    call_command("load_admin_organizations")

    # Verify no organizations were created
    assert AdminOrganization.objects.count() == 0
    assert len(AdminOrganization.objects.all()) == 0


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_with_single_organization(mock_file, mock_json_load):
    """Test that the command handles a single organization."""
    single_org_data = [
        {
            "id": "single-org.fi",
            "pref_label": {
                "fi": "Yksittäinen organisaatio",
                "en": "Single Organization",
            },
        },
    ]

    # Mock json.load to return single organization
    mock_json_load.return_value = single_org_data

    call_command("load_admin_organizations")

    # Verify organization was created
    assert AdminOrganization.objects.count() == 1
    assert len(AdminOrganization.objects.all()) == 1

    org = AdminOrganization.objects.get(id="single-org.fi")
    assert org.pref_label == {"fi": "Yksittäinen organisaatio", "en": "Single Organization"}


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_idempotent(mock_file, mock_json_load, mock_json_data):
    """Test that running the command multiple times is idempotent."""
    # Mock json.load to return our test data
    mock_json_load.return_value = mock_json_data

    # Run command first time
    call_command("load_admin_organizations")

    assert AdminOrganization.objects.count() == 2
    assert len(AdminOrganization.objects.all()) == 2

    # Get the organizations after first run
    org1 = AdminOrganization.objects.get(id="test-org-1.fi")
    org2 = AdminOrganization.objects.get(id="test-org-2.fi")

    # Run command second time
    call_command("load_admin_organizations")

    # Verify count remains the same
    assert AdminOrganization.objects.count() == 2
    assert len(AdminOrganization.objects.all()) == 2

    # Verify organizations still have the same data (idempotent)
    org1.refresh_from_db()
    org2.refresh_from_db()
    assert org1.pref_label == {"fi": "Test Organisaatio 1", "en": "Test Organization 1"}
    assert org2.pref_label == {"fi": "Test Organisaatio 2", "en": "Test Organization 2"}


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_with_null_pref_label(mock_file, mock_json_load):
    """Test that the command handles organizations with null pref_label."""
    org_data_with_null = [
        {
            "id": "null-label.fi",
            "pref_label": None,
        },
    ]

    # Mock json.load to return organization with null pref_label
    mock_json_load.return_value = org_data_with_null

    call_command("load_admin_organizations")

    # Verify organization was created
    assert AdminOrganization.objects.count() == 1
    assert len(AdminOrganization.objects.all()) == 1

    org = AdminOrganization.objects.get(id="null-label.fi")
    assert org.pref_label is None


@patch("apps.users.management.commands.load_admin_organizations.json.load")
@patch("builtins.open", create=True)
def test_load_admin_organizations_updates_existing_with_null_pref_label(mock_file, mock_json_load):
    """Test that the command updates existing organizations to null pref_label."""
    # Create an existing organization with a pref_label
    existing_org = AdminOrganization.objects.create(
        id="null-label.fi",
        pref_label={"fi": "Vanha nimi", "en": "Old name"},
    )

    org_data_with_null = [
        {
            "id": "null-label.fi",
            "pref_label": None,
        },
    ]

    # Mock json.load to return organization with null pref_label
    mock_json_load.return_value = org_data_with_null

    call_command("load_admin_organizations")

    # Verify organization was updated
    assert AdminOrganization.objects.count() == 1
    assert len(AdminOrganization.objects.all()) == 1

    # Verify the existing organization was updated to null pref_label
    existing_org.refresh_from_db()
    assert existing_org.pref_label is None
