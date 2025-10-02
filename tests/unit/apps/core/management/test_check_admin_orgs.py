import logging
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from io import StringIO
from apps.core import factories
from apps.files import factories as file_factories
from apps.core.models import Dataset


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_no_admin_org_mismatch(mock_ldap_class, dataset, caplog):
    """Test when no admin org mismatches exist."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = (
        "test-org"  # Same as metadata_owner.organization
    )
    print(Dataset.objects.all())
    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("check_admin_orgs")

    # Verify no mismatch was logged
    assert len(caplog.records) == 1
    assert "Datasets with admin org mismatch checked" in caplog.records[0].message

    # Verify check_admin_org_mismatch was called with correct project
    mock_ldap.check_admin_org_mismatch.assert_called_once_with("2001479")


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_admin_org_mismatch_found(mock_ldap_class, dataset, caplog):
    """Test when admin org mismatches are found and logged."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "different-admin-org"

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("check_admin_orgs")

    # Verify mismatch was logged
    assert len(caplog.records) == 2
    assert "Admin org mismatch" in caplog.records[0].message
    assert "Datasets with admin org mismatch checked" in caplog.records[1].message


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_no_admin_org_returned(mock_ldap_class, dataset, caplog):
    """Test when check_admin_org_mismatch returns None."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = None

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("check_admin_orgs")

    # Verify no mismatch was logged (since check_admin_org_mismatch returned None)
    assert len(caplog.records) == 1
    assert "Datasets with admin org mismatch checked" in caplog.records[0].message


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_only_ida_datasets_processed(mock_ldap_class, dataset, non_ida_dataset):
    """Test that only IDA datasets are processed."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "test-org"

    call_command("check_admin_orgs")

    # Verify check_admin_org_mismatch was called only once (for IDA dataset)
    mock_ldap.check_admin_org_mismatch.assert_called_once_with("2001479")


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_multiple_ida_datasets(mock_ldap_class, dataset, metadata_provider):
    """Test with multiple IDA datasets."""
    # Create another IDA dataset
    another_ida_storage = file_factories.FileStorageFactory(
        storage_service="ida", csc_project="2001480"
    )
    # Create dataset manually to ensure metadata_owner is used correctly
    from apps.core.models import Dataset

    another_dataset = factories.PublishedDatasetFactory(
        metadata_owner=metadata_provider,
        title={"en": "Another Dataset"},
    )
    # Create file_set with the dataset
    another_file_set = factories.FileSetFactory(
        dataset=another_dataset, storage=another_ida_storage
    )
    # Create related DatasetMetrics record
    factories.DatasetMetricsFactory(dataset=another_dataset)

    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "different-org"

    call_command("check_admin_orgs")

    # Verify check_admin_org_mismatch was called for both projects
    assert mock_ldap.check_admin_org_mismatch.call_count == 2
    mock_ldap.check_admin_org_mismatch.assert_any_call("2001479")
    mock_ldap.check_admin_org_mismatch.assert_any_call("2001480")


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_logging_format(mock_ldap_class, dataset, caplog):
    """Test the format of mismatch log messages."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.return_value = "admin-org-123"

    # Capture log output
    with caplog.at_level(logging.INFO):
        call_command("check_admin_orgs")

    # Verify the log message format
    mismatch_log = caplog.records[0].message
    assert "Dataset" in mismatch_log
    assert "Admin org mismatch" in mismatch_log
    assert "admin-org-123" in mismatch_log
    assert "test-org" in mismatch_log
    assert str(dataset.id) in mismatch_log


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_ldap_idm_exception_handling(mock_ldap_class, dataset):
    """Test behavior when LdapIdm raises an exception."""
    # Mock LdapIdm to raise an exception
    mock_ldap_class.side_effect = Exception("LDAP connection failed")

    # The command should propagate the exception
    with pytest.raises(Exception) as exc_info:
        call_command("check_admin_orgs")

    assert "LDAP connection failed" in str(exc_info.value)


@pytest.mark.django_db
@patch("apps.core.management.commands.check_admin_orgs.LdapIdm")
def test_check_admin_org_mismatch_exception_handling(mock_ldap_class, dataset):
    """Test behavior when check_admin_org_mismatch raises an exception."""
    # Mock LdapIdm instance
    mock_ldap = Mock()
    mock_ldap_class.return_value = mock_ldap
    mock_ldap.check_admin_org_mismatch.side_effect = Exception("LDAP query failed")

    # The command should propagate the exception
    with pytest.raises(Exception) as exc_info:
        call_command("check_admin_orgs")

    assert "LDAP query failed" in str(exc_info.value)
