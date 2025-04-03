import pytest
from django.conf import settings
from django.core import management

from apps.core import factories
from apps.refdata.models import License
from apps.rems.mocks import MockREMS
from apps.rems.models import (
    REMSCatalogueItem,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)
from apps.rems.rems_service import REMSError, REMSService

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture
def mock_rems(requests_mock):
    rems = MockREMS()
    rems.register_endpoints(requests_mock)
    management.call_command("create_initial_rems_entities")

    # Clear request history
    rems.clear_calls()
    requests_mock.reset_mock()
    return rems


def test_initial_rems_entities(mock_rems):
    assert REMSWorkflow.objects.get(key="automatic").rems_id == 1
    assert REMSUser.objects.get(key="approver-bot").rems_id == "approver-bot"
    assert REMSOrganization.objects.get(key="csc").rems_id == "csc"


def test_rems_service_create_dataset(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=catalog)
    REMSService().create_dataset(dataset)

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
    resource = mock_rems.entities["resource"][1]
    assert resource["resid"] == f"dataset-{dataset.id}"

    assert REMSCatalogueItem.objects.count() == 1
    item = mock_rems.entities["catalogue-item"][1]
    assert item["resid"] == f"dataset-{dataset.id}"
    assert item["resource-id"] == resource["id"]


def test_rems_service_create_dataset_twice(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=catalog)
    REMSService().create_dataset(dataset)
    assert mock_rems.calls == ["create/license", "create/resource", "create/catalogue-item"]
    mock_rems.clear_calls()
    REMSService().create_dataset(dataset)
    assert mock_rems.calls == ["get/license", "get/resource", "get/catalogue-item"]
    assert mock_rems.entities["catalogue-item"][1]["localizations"]["en"] == {
        "title": dataset.title["en"],
        "infourl": f"https://{settings.ETSIN_URL}/dataset/{dataset.id}",
    }


def test_rems_service_update_dataset_title(mock_rems):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=catalog)
    REMSService().create_dataset(dataset)
    mock_rems.clear_calls()

    dataset.title = {"en": "new title", "fi": "uus title"}
    dataset.save()
    REMSService().create_dataset(dataset)
    assert mock_rems.calls == [
        "get/license",
        "get/resource",
        "get/catalogue-item",
        "edit/catalogue-item",
    ]
    assert mock_rems.entities["catalogue-item"][1]["localizations"]["en"]["title"] == "new title"
    assert mock_rems.entities["catalogue-item"][1]["archived"] == False


def test_rems_service_update_dataset_license(mock_rems, license_reference_data):
    catalog = factories.DataCatalogFactory(rems_enabled=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=catalog)
    REMSService().create_dataset(dataset)

    mock_rems.clear_calls()
    lic = dataset.access_rights.license.first()
    lic.reference = License.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
    )
    lic.save()

    # License changed -> new resource -> new catalog item
    REMSService().create_dataset(dataset)
    assert mock_rems.calls == [
        "create/license",
        "get/resource",
        "disable/resource",
        "archive/resource",
        "create/resource",
        "get/catalogue-item",
        "disable/catalogue-item",
        "archive/catalogue-item",
        "create/catalogue-item",
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
    assert "REMS request was unsuccessful" in str(ec.value)
