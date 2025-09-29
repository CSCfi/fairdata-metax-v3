import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.core import factories
from apps.rems.rems_service import REMSService
from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def handler(fairdata_users_group):
    user, _created = MetaxUser.objects.get_or_create(
        username="rems_handler",
        fairdata_username="rems_handler",
        first_name="REMS",
        last_name="Handler",
        email="handler@example.com",
        is_hidden=False,
        admin_organizations=[],
        dac_organizations=["test_organization"],
    )
    _group, _ = Group.objects.get_or_create(name="fairdata_users")
    user.groups.set([fairdata_users_group])
    user.save()
    return user


@pytest.fixture
def handler_client(handler):
    client = Client()
    client._user = handler
    client.force_login(handler)
    return client


@pytest.fixture
def automatic_rems_dataset(mock_rems, user):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        access_rights__rems_approval_type="automatic",
        metadata_owner__user=user,
        metadata_owner__organization="test_organization",
    )
    return dataset


@pytest.fixture
def manual_rems_dataset(mock_rems, user):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        access_rights__rems_approval_type="manual",
        metadata_owner__user=user,
        metadata_owner__organization="test_organization",
    )
    return dataset


@pytest.fixture
def automatic_rems_application(automatic_rems_dataset, user, handler):
    service = REMSService()
    service.publish_dataset(automatic_rems_dataset)
    service.create_application_for_dataset(
        user, automatic_rems_dataset, service.get_dataset_rems_license_ids(automatic_rems_dataset)
    )


@pytest.fixture
def manual_rems_application(manual_rems_dataset, user, handler):
    service = REMSService()
    service.publish_dataset(manual_rems_dataset)
    service.create_application_for_dataset(
        user, manual_rems_dataset, service.get_dataset_rems_license_ids(manual_rems_dataset)
    )


def test_rems_applications_admin(mock_rems, admin_client):
    """Admin is not a Fairdata user and cannot have REMS applications."""
    res = admin_client.get("/v3/rems/applications")
    assert res.status_code == 403, res.dat


def test_list_rems_applications(
    mock_rems, user_client, user2_client, handler_client, automatic_rems_application
):
    """Only applicant and handlers can see an application."""
    res = user_client.get("/v3/rems/applications")
    assert res.status_code == 200
    assert len(res.data) == 1

    res = handler_client.get("/v3/rems/applications")
    assert res.status_code == 200
    assert len(res.data) == 1

    res = user2_client.get("/v3/rems/applications")
    assert res.status_code == 200
    assert len(res.data) == 0


def test_get_rems_application(
    mock_rems, user_client, user2_client, handler_client, automatic_rems_application
):
    """Only applicant and handlers can see an application."""
    res = user_client.get("/v3/rems/applications/1")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/1")
    assert res.status_code == 200

    res = user2_client.get("/v3/rems/applications/1")
    assert res.status_code == 404


def test_get_rems_applications_todo_handled(
    mock_rems, user, user_client, handler_client, manual_rems_application
):
    """Test 'todo' and 'handled' application views."""
    res = handler_client.get("/v3/rems/applications/todo")
    assert res.status_code == 200
    assert len(res.data) == 1

    res = handler_client.get("/v3/rems/applications/handled")
    assert res.status_code == 200
    assert len(res.data) == 0

    res = user_client.get("/v3/rems/applications/todo")
    assert res.status_code == 200
    assert len(res.data) == 0  # Only handlers can see 'todo' applications

    # Approve the application.
    # 'Todo' applications should be moved to 'handled' after approval.
    res = handler_client.post("/v3/rems/applications/1/approve")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/todo")
    assert res.status_code == 200
    assert len(res.data) == 0  # No more todo

    res = handler_client.get("/v3/rems/applications/handled")
    assert res.status_code == 200
    assert len(res.data) == 1  # Application has now been handled

    res = user_client.get("/v3/rems/applications/handled")
    assert res.status_code == 200
    assert len(res.data) == 0  # Only handlers can see 'handled' applications


def test_rems_applications_approve(
    mock_rems, user_client, handler_client, manual_rems_application
):
    res = user_client.post("/v3/rems/applications/1/approve")
    assert res.status_code == 403  # Only handler can approve

    res = handler_client.post("/v3/rems/applications/1/approve")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/1")
    assert res.status_code == 200
    assert res.data["application/state"] == "application.state/approved"
    assert len(mock_rems.entities["entitlement"]["test_user"]) == 1

    res = handler_client.post("/v3/rems/applications/1/approve")
    assert res.status_code == 403  # Approving twice is forbidden


def test_rems_applications_reject(mock_rems, user_client, handler_client, manual_rems_application):
    res = user_client.post("/v3/rems/applications/1/reject")
    assert res.status_code == 403  # Only handler can reject

    res = handler_client.post("/v3/rems/applications/1/reject")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/1")
    assert res.status_code == 200
    assert res.data["application/state"] == "application.state/rejected"
    assert len(mock_rems.entities["entitlement"]) == 0

    res = handler_client.post("/v3/rems/applications/1/reject")
    assert res.status_code == 403  # Rejecting twice is forbidden


def test_rems_applications_close_submitted(
    mock_rems, user_client, handler_client, manual_rems_application
):
    """Close application in 'submitted' state."""
    res = user_client.post("/v3/rems/applications/1/close")
    assert res.status_code == 403  # Only handler can close

    res = handler_client.post("/v3/rems/applications/1/close")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/1")
    assert res.status_code == 200
    assert res.data["application/state"] == "application.state/closed"
    assert len(mock_rems.entities["entitlement"]) == 0


def test_rems_applications_close_approved(
    mock_rems, user_client, handler_client, automatic_rems_application
):
    """Close application in 'approved' state."""
    res = user_client.post("/v3/rems/applications/1/close")
    assert res.status_code == 403  # Only handler can close

    res = handler_client.post("/v3/rems/applications/1/close")
    assert res.status_code == 200

    res = handler_client.get("/v3/rems/applications/1")
    assert res.status_code == 200
    assert res.data["application/state"] == "application.state/closed"

    # Existing entitlement should be ended
    assert len(mock_rems.entities["entitlement"]["test_user"]) == 1
    assert mock_rems.entities["entitlement"]["test_user"][1]["end"] is not None
