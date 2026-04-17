import uuid
from django.test import override_settings
import pytest
from django.conf import settings
from django.core import mail
from rest_framework.exceptions import ValidationError

from apps.core import factories
from apps.refdata.models import License
from apps.rems.models import (
    REMSCatalogueItem,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)
from apps.rems.rems_service import REMSService
from apps.rems.rems_session import REMSError
from apps.users.models import AdminOrganization

pytestmark = [pytest.mark.django_db]


def test_initial_rems_entities(mock_rems):
    assert REMSUser.objects.get(key="approver-bot").rems_id == "approver-bot"
    assert REMSUser.objects.get(key="rejecter-bot").rems_id == "rejecter-bot"
    assert REMSOrganization.objects.get(key="csc").rems_id == "csc"


def test_rems_service_publish_dataset(mock_rems, user):
    """Test publishing dataset to REMS."""
    user.admin_organizations = ["test_organization"]
    user.save()

    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__admin_organization=user.organization
    )
    REMSService().publish_dataset(dataset, raise_errors=True)

    assert REMSLicense.objects.count() == 1
    lic = mock_rems.entities["license"][1]
    assert lic["licensetype"] == "link"
    assert lic["localizations"] == {
        "en": {
            "textcontent": "http://uri.suomi.fi/codelist/fairdata/license/code/other",
            "title": "Other",
        },
        "fi": {
            "textcontent": "http://uri.suomi.fi/codelist/fairdata/license/code/other",
            "title": "Muu",
        },
    }

    assert REMSResource.objects.count() == 1
    assert len(mock_rems.entities["resource"]) == 1
    resource = mock_rems.entities["resource"][1]
    assert resource["resid"] == f"metax-test:{dataset.id}"

    assert REMSCatalogueItem.objects.count() == 1
    item = mock_rems.entities["catalogue-item"][1]
    assert item["resid"] == f"metax-test:{dataset.id}"
    assert item["resource-id"] == resource["id"]

    assert REMSWorkflow.objects.count() == 1
    workflow = mock_rems.entities["workflow"][1]
    assert set(u["userid"] for u in workflow["workflow"]["handlers"]) == {
        "approver-bot",
        "rejecter-bot",
        "owner",
        "test_user",
    }


def test_rems_service_publish_dataset_twice(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(data_catalog=catalog)
    REMSService().publish_dataset(dataset)
    assert mock_rems.call_list == [
        "create/workflow->1",
        "create/license->1",
        "create/resource->1",
        "create/catalogue-item->1",
    ]
    mock_rems.clear_calls()
    REMSService().publish_dataset(dataset, raise_errors=True)
    assert mock_rems.call_list == [
        "get/catalogue-item:1",
        "get/workflow:1",
        "get/resource:1",
        "get/license:1",
        "get/resource:1",
        "get/catalogue-item:1",
    ]
    assert mock_rems.entities["catalogue-item"][1]["localizations"]["en"] == {
        "title": dataset.title["en"],
        "infourl": f"https://{settings.ETSIN_URL}/dataset/{dataset.id}",
    }


def test_rems_service_publish_non_rems_dataset(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=catalog)
    with pytest.raises(ValueError) as ec:
        REMSService().publish_dataset(dataset)
    assert str(ec.value) == "Dataset is not enabled for REMS."


def test_rems_service_update_dataset_title(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(data_catalog=catalog)
    REMSService().publish_dataset(dataset)
    mock_rems.clear_calls()

    dataset.title = {"en": "new title", "fi": "uus title"}
    dataset.save()
    REMSService().publish_dataset(dataset)
    assert mock_rems.call_list == [
        "get/catalogue-item:1",
        "get/workflow:1",
        "get/resource:1",
        "get/license:1",
        "get/resource:1",
        "get/catalogue-item:1",
        "edit/catalogue-item:1",
    ]
    assert mock_rems.entities["catalogue-item"][1]["localizations"]["en"]["title"] == "new title"
    assert mock_rems.entities["catalogue-item"][1]["archived"] == False


def test_rems_service_update_dataset_license(mock_rems, license_reference_data):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(data_catalog=catalog, id=uuid.UUID(int=7))
    REMSService().publish_dataset(dataset)

    mock_rems.clear_calls()
    lic = dataset.access_rights.license.first()
    lic.reference = License.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
    )
    lic.save()

    # License changed -> new resource -> new catalog item
    REMSService().publish_dataset(dataset, raise_errors=True)
    assert mock_rems.call_list == [
        "get/catalogue-item:1",
        "get/workflow:1",
        "get/resource:1",
        "create/license->2",
        "list/application?query=resource:%22metax-test:00000000-0000-0000-0000-000000000007%22",
        "get/resource:1",
        "get/resource:1",
        "list/catalogue-item?resource=metax-test%3a00000000-0000-0000-0000-000000000007&archived=false",
        "disable/catalogue-item:1",
        "archive/catalogue-item:1",
        "disable/resource:1",
        "archive/resource:1",
        "create/resource->2",
        "create/catalogue-item->2",
    ]
    # New entity should have new resource with new license
    assert (
        mock_rems.entities["resource"][2]["licenses"][0]["localizations"]["en"]["textcontent"]
        == "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
    )
    assert (
        mock_rems.entities["catalogue-item"][2]["resource-id"]
        == mock_rems.entities["resource"][2]["id"]
    )
    assert mock_rems.entities["catalogue-item"][2]["archived"] == False

    # Old entity should be archived but otherwise unchanged
    assert (
        mock_rems.entities["resource"][1]["licenses"][0]["localizations"]["en"]["textcontent"]
        == "http://uri.suomi.fi/codelist/fairdata/license/code/other"
    )
    assert (
        mock_rems.entities["catalogue-item"][1]["resource-id"]
        == mock_rems.entities["resource"][1]["id"]
    )
    assert mock_rems.entities["catalogue-item"][1]["archived"] == True


def test_rems_service_update_dataset_terms(mock_rems, license_reference_data):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(data_catalog=catalog, id=uuid.UUID(int=7))
    dataset.access_rights.license.set([])
    dataset.access_rights.data_access_terms = {"en": "Old terms"}
    dataset.access_rights.save()
    REMSService().publish_dataset(dataset, raise_errors=True)

    mock_rems.clear_calls()
    dataset.access_rights.data_access_terms = {"en": "New terms"}
    dataset.access_rights.save()
    REMSService().publish_dataset(dataset, raise_errors=True)

    # The license created from data_access_terms needs to be updated.
    # License dependencies (catalogue item and resource) need to be archived first
    # before the license can be archived
    assert mock_rems.call_list == [
        "get/catalogue-item:1",
        "get/workflow:1",
        "get/resource:1",
        "get/license:1",
        "list/resource?resid=metax-test%3a00000000-0000-0000-0000-000000000007&archived=false",
        "get/resource:1",
        "list/catalogue-item?resource=metax-test%3a00000000-0000-0000-0000-000000000007&archived=false",
        "disable/catalogue-item:1",  # Archive old catalogue item
        "archive/catalogue-item:1",
        "disable/resource:1",
        "archive/resource:1",  # Archive old resource
        "disable/license:1",
        "archive/license:1",  # Archive old license
        "create/license->2",  # Create new license, resource and catalogue item
        "list/application?query=resource:%22metax-test:00000000-0000-0000-0000-000000000007%22",
        "create/resource->2",
        "create/catalogue-item->2",
    ]
    # New entity should have new resource with new license
    assert (
        mock_rems.entities["resource"][1]["licenses"][0]["localizations"]["en"]["textcontent"]
        == "Old terms"
    )
    assert (
        mock_rems.entities["resource"][2]["licenses"][0]["localizations"]["en"]["textcontent"]
        == "New terms"
    )


def test_rems_service_as_user(requests_mock, mock_rems):
    service = REMSService()
    service.session.get("/api/catalogue-items")
    with service.session.as_user("fd_teppo3"):
        service.session.get("/api/catalogue-items")
    service.session.get("/api/catalogue-items")
    assert requests_mock.call_count == 3
    assert [req.headers.get("x-rems-user-id") for req in requests_mock.request_history] == [
        "owner",
        "fd_teppo3",
        "owner",
    ]


def test_rems_service_http_error(requests_mock, mock_rems):
    with pytest.raises(REMSError) as ec:
        service = REMSService()
        service.session.get("/api/catalogue-items/123")
    assert ec.value.response.status_code == 404


def test_rems_service_success_false(mock_rems):
    """Handle special case where failed request has 200 status."""
    data = {
        "organization/id": "org",
        "organization/name": {"en": "org"},
        "organization/short-name": {"en": "organization"},
    }
    service = REMSService()
    service.session.post("/api/organizations/create", json=data)

    # Creating same organization twice returns 200 with success=False.
    with pytest.raises(REMSError) as ec:
        service.session.post("/api/organizations/create", json=data)
    assert ec.value.response.status_code == 200  # Response failed successfully?
    assert "REMS request" in str(ec.value)
    assert "was unsuccessful" in str(ec.value)


def test_rems_service_create_application_with_autoapprove(mock_rems, user, handler):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        access_rights__rems_approval_type="automatic",
    )
    service = REMSService()
    service.publish_dataset(dataset)
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )
    applications = service.get_user_applications_for_dataset(user, dataset)
    assert len(applications) == 1
    assert applications[0]["application/state"] == "application.state/approved"
    handlers = [
        user["userid"]
        for user in applications[0]["application/workflow"]["workflow.dynamic/handlers"]
    ]
    assert handlers == ["approver-bot", "rejecter-bot", "owner", "rems_handler"]

    # Check entitlement has been created
    entitlements = service.get_user_entitlements_for_dataset(user, dataset)
    assert len(entitlements) == 1
    assert entitlements[0]["resource"] == f"metax-test:{dataset.id}"

    assert len(mail.outbox) == 2

    # "New application" mail to handlers
    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.to == [handler.email]
    assert "New Data Use Application" in msg.subject
    assert "new data use application has been submitted" in msg.body

    # "Request processed" mail to applicant
    msg = mail.outbox[1]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.to == [user.email]
    assert "request has been approved" in msg.subject
    assert "request was reviewed" in msg.body


def test_rems_service_dac_email(mock_rems, user, handler):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        access_rights__rems_approval_type="automatic",
    )

    # Admin organization has dac_email sent, handler email should be sent there
    admin_org = AdminOrganization.objects.get(id=dataset.metadata_owner.admin_organization)
    admin_org.dac_email = "dac_email@example.com"
    admin_org.save()

    service = REMSService()
    service.publish_dataset(dataset)
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )

    # "New application" mail to admin_org.dac_email address
    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.to == ["dac_email@example.com"]
    assert "New Data Use Application" in msg.subject


def test_rems_service_manual_approval_form(mock_rems, user):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, access_rights__rems_approval_type="manual"
    )
    service = REMSService()
    service.publish_dataset(dataset)

    assert len(mock_rems.entities["form"]) == 1
    form = mock_rems.entities["form"][1]
    fields = [
        {
            "id": field["field/id"],
            "type": field["field/type"],
            "title": field["field/title"]["en"],
            "optional": field["field/optional"],
        }
        for field in form["form/fields"]
    ]
    assert fields == [
        {
            "id": "project_description",
            "type": "text",
            "title": "Description of your research project",
            "optional": False,
        },
        {
            "id": "access_control",
            "type": "text",
            "title": "Procedures to prevent unauthorized access to the requested data",
            "optional": True,
        },
        {
            "id": "other_persons",
            "type": "text",
            "title": "Other persons presumed to get access to the requested data",
            "optional": True,
        },
    ]


def test_rems_service_update_manual_approval_form(mock_rems, user):
    service = REMSService()
    service.create_manual_application_form()
    forms = mock_rems.entities["form"]
    assert len(forms) == 1
    forms[1]["form/fields"][0]["field/title"]["en"] = "Some other title"

    service.create_manual_application_form()
    assert len(forms) == 2
    assert forms[1]["form/fields"][0]["field/title"]["en"] == "Some other title"
    assert forms[1]["enabled"] == False
    assert (
        forms[2]["form/fields"][0]["field/title"]["en"] == "Description of your research project"
    )


def test_rems_service_emails(mock_rems, user, handler):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, access_rights__rems_approval_type="manual"
    )
    service = REMSService()
    service.publish_dataset(dataset)
    service.create_application_for_dataset(
        user,
        dataset,
        accept_licenses=service.get_dataset_rems_license_ids(dataset),
        field_values=[
            {
                "form": 1,
                "field": "project_description",
                "value": "some project description",
            }
        ],
    )
    applications = service.get_user_applications_for_dataset(user, dataset)
    assert len(applications) == 1
    assert applications[0]["application/state"] == "application.state/submitted"
    handlers = [
        user["userid"]
        for user in applications[0]["application/workflow"]["workflow.dynamic/handlers"]
    ]
    assert handlers == ["rejecter-bot", "owner", "rems_handler"]  # no approver-bot

    # Check no entitlement has been created
    entitlements = service.get_user_entitlements_for_dataset(user, dataset)
    assert len(entitlements) == 0

    # "New application" mail to handlers
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.to == [handler.email]
    assert "New Data Use Application" in msg.subject
    assert "new data use application has been submitted" in msg.body


@pytest.mark.parametrize(
    "command,event_en,event_fi",
    [
        ["approve_application", "been approved", "on hyväksytty"],
        ["reject_application", "been rejected", "on hylätty"],
        ["return_application", "been returned", "on palautettu"],
        ["close_application", "been closed", "on suljettu"],
        # Revoke not yet supported by REMSService
        # ["revoke_application", "been revoked", "on peruttu"],
    ],
)
def test_rems_service_application_manual_command_emails(
    mock_rems, user, handler, command, event_en, event_fi
):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, access_rights__rems_approval_type="manual"
    )
    service = REMSService()
    service.publish_dataset(dataset)
    application = service.create_application_for_dataset(
        user,
        dataset,
        accept_licenses=service.get_dataset_rems_license_ids(dataset),
        field_values=[
            {
                "form": 1,
                "field": "project_description",
                "value": "some project description",
            }
        ],
    )

    mail.outbox.clear()
    command_func = getattr(service, command)
    command_func(handler, application_id=application["application-id"], comment="hello world")

    msg = mail.outbox[0]
    assert msg.from_email == "test-sender@fairdata.fi"
    assert msg.to == [user.email]
    assert event_en in msg.subject
    assert event_en in msg.body
    assert event_fi in msg.subject
    assert event_fi in msg.body


def test_rems_service_create_application_dataset_not_published_to_rems(mock_rems, user):
    dataset = factories.REMSDatasetFactory(access_rights__rems_approval_type="automatic")
    service = REMSService()
    with pytest.raises(ValueError) as ec:
        service.create_application_for_dataset(user, dataset, [])
    assert str(ec.value) == "Dataset has not been published to REMS."


def test_rems_service_create_application_missing_license(mock_rems, user):
    dataset = factories.REMSDatasetFactory(access_rights__rems_approval_type="automatic")
    service = REMSService()
    service.publish_dataset(dataset)
    with pytest.raises(ValidationError) as ec:
        service.create_application_for_dataset(user, dataset, accept_licenses=[])
    assert str(ec.value.detail[0]) == "All licenses need to be accepted. Missing: [1]"


def test_rems_service_create_application_extra_license(mock_rems, user):
    dataset = factories.REMSDatasetFactory(access_rights__rems_approval_type="automatic")
    service = REMSService()
    service.publish_dataset(dataset)
    with pytest.raises(ValidationError) as ec:
        service.create_application_for_dataset(user, dataset, accept_licenses=[1, 12345])
    assert (
        str(ec.value.detail[0])
        == "The following licenses are not available for the application: [12345]"
    )


def test_rems_service_publish_dataset_custom_license_link(mock_rems):
    dataset = factories.REMSDatasetFactory()
    lic = factories.DatasetLicenseFactory(
        title={"en": "License name", "fi": "Lisenssin nimi"}, custom_url="https://license.url"
    )
    dataset.access_rights.license.set([lic])
    REMSService().publish_dataset(dataset, raise_errors=True)

    assert REMSLicense.objects.count() == 1
    lic = mock_rems.entities["license"][1]
    assert lic["licensetype"] == "link"
    assert lic["localizations"] == {
        "en": {
            "title": "License name",
            "textcontent": "https://license.url",
        },
        "fi": {
            "title": "Lisenssin nimi",
            "textcontent": "https://license.url",
        },
    }


def test_rems_service_publish_dataset_custom_license_text(mock_rems):
    dataset = factories.REMSDatasetFactory()
    lic = factories.DatasetLicenseFactory(
        title={"en": "License name", "fi": "Lisenssin nimi"},
        description={"en": "License text", "fi": "Lisenssin teksti"},
    )
    dataset.access_rights.license.set([lic])
    REMSService().publish_dataset(dataset, raise_errors=True)

    assert REMSLicense.objects.count() == 1
    lic = mock_rems.entities["license"][1]
    assert lic["licensetype"] == "text"
    assert lic["localizations"] == {
        "en": {
            "title": "License name",
            "textcontent": "License text",
        },
        "fi": {
            "title": "Lisenssin nimi",
            "textcontent": "Lisenssin teksti",
        },
    }


def test_rems_service_publish_dataset_custom_license_update(mock_rems, user):
    dataset = factories.REMSDatasetFactory()
    lic = factories.DatasetLicenseFactory(
        title={"en": "License name"}, description={"en": "License text"}
    )
    dataset.access_rights.license.set([lic])
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses.count() == 1

    # Create and auto-approve application
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )
    application = mock_rems.entities["application"][1]
    assert application["application/state"] == "application.state/approved"

    # Edit license -> applications should close
    lic.description = {"en": "New license text"}
    lic.save()
    service.publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses.count() == 1

    assert REMSLicense.all_objects.count() == 2  # Old license soft deleted
    assert REMSLicense.objects.count() == 1
    lic = mock_rems.entities["license"][2]
    assert lic["licensetype"] == "text"
    assert lic["localizations"] == {
        "en": {
            "title": "License name",
            "textcontent": "New license text",
        }
    }

    # Application should now be closed
    application = mock_rems.entities["application"][1]
    assert application["application/state"] == "application.state/closed"
    assert any(
        evt["event/type"] == "application.event/closed"
        for evt in application["application/events"]
    )


def test_rems_service_publish_dataset_custom_license_update_no_changes(mock_rems, user):
    dataset = factories.REMSDatasetFactory()
    lic = factories.DatasetLicenseFactory(
        title={"en": "License name"}, description={"en": "License text"}
    )
    dataset.access_rights.license.set([lic])
    service = REMSService()
    service.publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses.count() == 1

    # Create and auto-approve application
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )

    # Publish dataset again without changes to licenses -> application unchanged
    service.publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses.count() == 1

    assert REMSLicense.all_objects.count() == 1  # No license changes

    application = mock_rems.entities["application"][1]
    assert application["application/state"] == "application.state/approved"


def test_rems_service_publish_dataset_custom_license_remove(mock_rems):
    """Removing custom license from dataset should deprecate it."""
    dataset = factories.REMSDatasetFactory()
    ref_lic = factories.DatasetLicenseFactory(
        reference__url="http://uri.suomi.fi/codelist/fairdata/license/code/CC0-1.0"
    )
    ref_lic2 = factories.DatasetLicenseFactory()
    custom_lic = factories.DatasetLicenseFactory(
        title={"en": "License name"}, description={"en": "License text"}
    )
    custom_lic_2 = factories.DatasetLicenseFactory(
        title={"en": "Other license name"}, description={"en": "Other license text"}
    )
    dataset.access_rights.license.set([ref_lic, custom_lic, ref_lic2, custom_lic_2])
    REMSService().publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses.count() == 2

    dataset.access_rights.license.set([ref_lic, custom_lic])
    REMSService().publish_dataset(dataset, raise_errors=True)
    assert dataset.custom_rems_licenses(manager="all_objects").count() == 1
    lic_data = mock_rems.entities["license"][dataset.custom_rems_licenses.first().rems_id]
    assert lic_data["localizations"]["en"]["textcontent"] == "License text"

    assert REMSLicense.all_objects.count() == 4
    assert REMSLicense.objects.count() == 3


def test_rems_service_get_license_type_errors():
    service = REMSService()
    with pytest.raises(ValueError):
        service.get_license_type(url=None, description=None)
    with pytest.raises(ValueError):
        service.get_license_type(url="https://www.example.com", description={"en": "License text"})


def test_rems_service_publish_dataset_change_admin_org(mock_rems, user):
    """Test REMS publish when changing admin organization for dataset."""
    user.admin_organizations = ["test_organization"]
    user.save()
    service = REMSService()
    AdminOrganization.objects.create(id="admin_org1")
    AdminOrganization.objects.create(id="admin_org2")

    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__admin_organization="admin_org1"
    )
    service.publish_dataset(dataset, raise_errors=True)

    assert len(mock_rems.entities["workflow"]) == 1
    assert len(mock_rems.entities["license"]) == 1
    assert len(mock_rems.entities["resource"]) == 1
    assert len(mock_rems.entities["catalogue-item"]) == 1

    # Create auto-approved application
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )
    assert len(mock_rems.entities["application"]) == 1
    assert (
        mock_rems.entities["application"][1]["application/state"] == "application.state/approved"
    )

    # Change admin_organization. Dataset should close REMS applications and change workflow
    dataset.metadata_owner = factories.MetadataProviderFactory(
        user=dataset.metadata_owner.user,
        organization=dataset.metadata_owner.organization,
        admin_organization="admin_org2",
    )
    dataset.save()

    service.publish_dataset(dataset, raise_errors=True)

    # A workflow for admin_org_2 is created along with a catalogue item that uses the new workflow.
    # The existing license and resource are unchanged.
    assert len(mock_rems.entities["workflow"]) == 2
    assert len(mock_rems.entities["catalogue-item"]) == 2
    assert len(mock_rems.entities["resource"]) == 1
    assert len(mock_rems.entities["license"]) == 1

    # The old catalogue item is archived.
    # The old workflow may be in use in other datasets and is not archived.
    assert mock_rems.entities["catalogue-item"][1]["archived"] == True
    assert mock_rems.entities["catalogue-item"][1]["wfid"] == 1
    assert mock_rems.entities["workflow"][1]["archived"] == False
    assert mock_rems.entities["workflow"][2]["archived"] == False
    assert mock_rems.entities["catalogue-item"][2]["archived"] == False
    assert mock_rems.entities["catalogue-item"][2]["wfid"] == 2

    # The old application is closed
    assert len(mock_rems.entities["application"]) == 1
    assert mock_rems.entities["application"][1]["application/state"] == "application.state/closed"
    assert (
        mock_rems.entities["application"][1]["application/events"][-1]["event/type"]
        == "application.event/closed"
    )
    assert (
        mock_rems.entities["application"][1]["application/events"][-1]["application/comment"]
        == "Permission granter organization has changed."
    )


def test_rems_service_publish_dataset_missing_admin_organization(mock_rems, user):
    """Test publishing dataset to REMS without admin organization."""
    user.admin_organizations = ["test_organization"]
    user.save()

    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog, metadata_owner__admin_organization=None
    )
    with pytest.raises(ValueError) as ec:
        REMSService().publish_dataset(dataset, raise_errors=True)

    assert str(ec.value) == "Dataset is not enabled for REMS."

    with pytest.raises(ValueError) as ec:
        REMSService().create_dataset_workflow(dataset)  # Try creating workflow directly

    assert str(ec.value) == "Dataset is missing admin_organization."


def test_rems_service_get_application_dataset(mock_rems, user):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.REMSDatasetFactory(
        data_catalog=catalog,
        access_rights__rems_approval_type="automatic",
    )
    service = REMSService()
    service.publish_dataset(dataset)
    service.create_application_for_dataset(
        user, dataset, service.get_dataset_rems_license_ids(dataset)
    )

    application = mock_rems.entities["application"][1]
    assert service.get_application_dataset(application) == dataset

    application["application/resources"][0]["resource/ext-id"] += "höps"
    assert service.get_application_dataset(application) is None

    del application["application/resources"][0]["resource/ext-id"]
    assert service.get_application_dataset(application) is None
