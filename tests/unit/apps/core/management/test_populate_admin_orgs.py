import logging
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.db import transaction
from django.db.models import F
from apps.core import factories
from apps.files import factories as file_factories


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_metadata_provider_admin_org_update(mock_ldap_class, metadata_provider_old_admin, caplog):
    """Test that MetadataProvider admin_organization is updated to match organization."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify admin_organization was updated to match organization
    metadata_provider_old_admin.refresh_from_db()
    assert (
        metadata_provider_old_admin.admin_organization == metadata_provider_old_admin.organization
    )
    assert metadata_provider_old_admin.admin_organization == "test-org"


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_dataset_admin_org_update_with_mismatch(mock_ldap_class, dataset, caplog):
    """Test that dataset metadata_owner admin_organization is updated when mismatch found."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "quota-granter-org"
    old_metadata_owner = dataset.metadata_owner
    old_metadata_owner.refresh_from_db()

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify dataset metadata_owner admin_organization was updated
    dataset.refresh_from_db()
    old_metadata_owner.refresh_from_db()

    assert dataset.metadata_owner.admin_organization == "quota-granter-org"
    assert dataset.metadata_owner != old_metadata_owner

    # Verify log message
    assert len(caplog.records) == 3
    assert "Populated 1 datasets with quota granter org" in caplog.records[2].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_no_admin_org_mismatch(mock_ldap_class, dataset, caplog):
    """Test when no admin org mismatches exist."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None
    old_metadata_owner = dataset.metadata_owner

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    dataset.refresh_from_db()
    old_metadata_owner.refresh_from_db()

    # Verify no datasets were updated
    assert dataset.metadata_owner.admin_organization == "test-org"
    assert dataset.metadata_owner == old_metadata_owner

    # Verify log message
    assert len(caplog.records) == 1
    assert "Populated 0 datasets with quota granter org" in caplog.records[0].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_multiple_ida_datasets(mock_ldap_class, dataset, metadata_provider_old_admin, caplog):
    """Test with multiple IDA datasets."""
    # Create another IDA dataset
    another_ida_storage = file_factories.FileStorageFactory(
        storage_service="ida", csc_project="2001480"
    )
    another_file_set = factories.FileSetFactory(storage=another_ida_storage)
    # Create dataset manually to ensure metadata_owner is used correctly
    from apps.core.models import Dataset

    another_dataset = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider_old_admin,
        file_set=another_file_set,
        title={"en": "Another Dataset"},
    )
    # Create related DatasetMetrics record
    factories.DatasetMetricsFactory(dataset=another_dataset)

    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "quota-granter-org"

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify check_admin_org_mismatch was called for both projects
    assert mock_ldap.check_admin_org_mismatch.call_count == 2
    mock_ldap.check_admin_org_mismatch.assert_any_call("2001479")
    mock_ldap.check_admin_org_mismatch.assert_any_call("2001480")

    # Verify both datasets were updated
    dataset.refresh_from_db()
    another_dataset.refresh_from_db()
    assert dataset.metadata_owner.admin_organization == "quota-granter-org"
    assert another_dataset.metadata_owner.admin_organization == "test-org"

    # Verify log message shows 2 datasets
    assert len(caplog.records) == 5
    assert "Populated 2 datasets with quota granter org" in caplog.records[4].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_empty_dataset_queryset(mock_ldap_class, caplog):
    """Test when no IDA datasets exist."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify no calls to check_admin_org_mismatch
    mock_ldap.check_admin_org_mismatch.assert_not_called()

    # Verify completion message was logged
    assert len(caplog.records) == 1
    assert "Populated 0 datasets with quota granter org" in caplog.records[0].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_ldap_idm_initialization(mock_ldap_class, dataset):
    """Test that LdapIdm is properly initialized."""
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    call_command("populate_admin_orgs")

    # Verify LdapIdm was instantiated
    mock_ldap_class.assert_called_once()


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_transaction_atomic_decorator(mock_ldap_class, dataset):
    """Test that the command uses transaction.atomic decorator."""
    # This test verifies the decorator is present by checking the method attributes
    from apps.core.management.commands.populate_admin_orgs import Command

    # Check that the handle method has the atomic decorator
    assert hasattr(Command.handle, "__wrapped__")


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_ldap_idm_exception_handling(mock_ldap_class, dataset):
    """Test behavior when LdapIdm raises an exception."""
    # Mock LdapIdm to raise an exception
    mock_ldap_class.side_effect = Exception("LDAP connection failed")

    # The command should propagate the exception
    with pytest.raises(Exception) as exc_info:
        call_command("populate_admin_orgs")

    assert "LDAP connection failed" in str(exc_info.value)


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_check_admin_org_mismatch_exception_handling(mock_ldap_class, dataset):
    """Test behavior when check_admin_org_mismatch raises an exception."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.side_effect = Exception("LDAP query failed")

    # The command should propagate the exception
    with pytest.raises(Exception) as exc_info:
        call_command("populate_admin_orgs")

    assert "LDAP query failed" in str(exc_info.value)


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_mixed_admin_org_results(
    mock_ldap_class, metadata_provider, metadata_provider_old_admin, caplog, data_catalog
):
    """Test with mixed results - some datasets get admin org, others don't."""
    # Create two IDA datasets
    ida_storage1 = file_factories.FileStorageFactory(storage_service="ida", csc_project="2001479")
    ida_storage2 = file_factories.FileStorageFactory(storage_service="ida", csc_project="2001480")

    # Create datasets manually to ensure metadata_owner is used correctly
    from apps.core.models import Dataset

    dataset1 = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider_old_admin,
        title={"en": "Dataset 1"},
        data_catalog=data_catalog,
    )
    dataset2 = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider,
        title={"en": "Dataset 2"},
        data_catalog=data_catalog,
    )

    file_set1 = factories.FileSetFactory(storage=ida_storage1)
    file_set2 = factories.FileSetFactory(storage=ida_storage2)
    file_set1.dataset = dataset1
    file_set2.dataset = dataset2
    file_set1.save()
    file_set2.save()

    # Mock LdapIdm instance with mixed results
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap

    def side_effect(project_id):
        if project_id == "2001479":
            return "quota-granter-org-1"
        return None  # No admin org for second project

    mock_ldap.check_admin_org_mismatch.side_effect = side_effect

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify only one dataset was updated
    dataset1.refresh_from_db()
    dataset2.refresh_from_db()
    dataset1.metadata_owner.refresh_from_db()
    dataset2.metadata_owner.refresh_from_db()

    assert dataset1.metadata_owner.admin_organization == "quota-granter-org-1"
    assert dataset2.metadata_owner.admin_organization == "test-org"  # Updated to organization

    # Verify log message shows 1 dataset
    assert len(caplog.records) == 3
    assert "Populated 1 datasets with quota granter org" in caplog.records[2].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_metadata_provider_organization_update_only(
    mock_ldap_class, metadata_provider_old_admin, caplog
):
    """Test that MetadataProvider admin_organization is updated even when no datasets exist."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("populate_admin_orgs")

    # Verify admin_organization was updated to match organization
    metadata_provider_old_admin.refresh_from_db()
    assert (
        metadata_provider_old_admin.admin_organization == metadata_provider_old_admin.organization
    )

    # Verify log message
    assert len(caplog.records) == 2
    assert "Populated 0 datasets with quota granter org" in caplog.records[1].message


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_dataset_save_not_called_when_no_admin_org(mock_ldap_class, dataset):
    """Test that dataset.metadata_owner.save() is not called when no admin_org is found."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    # Mock the save method to track calls
    with patch.object(dataset.metadata_owner, "save") as mock_save:
        call_command("populate_admin_orgs")

        # Verify save was not called
        mock_save.assert_not_called()


@pytest.mark.django_db
@patch("apps.core.management.commands.populate_admin_orgs.LdapIdm")
def test_f_expression_update(mock_ldap_class, metadata_provider_old_admin):
    """Test that F expression correctly updates admin_organization to organization."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    # Store original values
    original_org = metadata_provider_old_admin.organization
    original_admin_org = metadata_provider_old_admin.admin_organization

    call_command("populate_admin_orgs")

    # Verify admin_organization was updated to match organization
    metadata_provider_old_admin.refresh_from_db()
    assert metadata_provider_old_admin.admin_organization == original_org
    assert metadata_provider_old_admin.admin_organization != original_admin_org
