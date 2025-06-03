import pytest
from django.conf import settings

from apps.core import factories
from apps.core.models.catalog_record.dataset import Dataset, REMSStatus
from apps.refdata.models import License
from apps.rems.models import REMSCatalogueItem, REMSLicense
from apps.rems.rems_service import REMSService

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def rems_dataset_json(dataset_a_json):
    access_rights = dataset_a_json["access_rights"]
    access_rights["access_type"] = {
        "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/permit"
    }
    access_rights["restriction_grounds"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"}
    ]
    access_rights["rems_approval_type"] = "automatic"
    return dataset_a_json


def test_dataset_rems_approval_type(
    admin_client, rems_dataset_json, data_catalog, reference_data, settings
):
    res = admin_client.post("/v3/datasets", rems_dataset_json, content_type="application/json")
    assert res.status_code == 400

    settings.REMS_ENABLED = True
    res = admin_client.post("/v3/datasets", rems_dataset_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["access_rights"]["rems_approval_type"] == "automatic"


def test_publish_rems_dataset(
    mock_rems, admin_client, rems_dataset_json, data_catalog, reference_data
):
    res = admin_client.post("/v3/datasets", rems_dataset_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.rems_publish_error is None
    assert dataset.rems_status == REMSStatus.PUBLISHED

    catalogue_items = REMSCatalogueItem.objects.filter(key=f"dataset-{res.data['id']}")
    assert catalogue_items.count() == 1
    item = catalogue_items.first()
    assert dataset.rems_id == item.rems_id


def test_rems_dataset_data_access_fields(
    mock_rems, admin_client, user_client, rems_dataset_json, data_catalog, reference_data
):
    access_rights = rems_dataset_json["access_rights"]
    access_rights["data_access_application_instructions"] = {"en": "This is how you apply"}
    access_rights["data_access_terms"] = {"en": "Terms here", "fi": "Käyttöehdot tähän"}
    access_rights["data_access_reviewer_instructions"] = {"en": "plz review"}

    res = admin_client.post("/v3/datasets", rems_dataset_json, content_type="application/json")
    assert res.status_code == 201
    dataset = Dataset.objects.get(id=res.data["id"])
    assert dataset.rems_publish_error is None
    assert dataset.rems_status == REMSStatus.PUBLISHED

    # Creator should see all fields
    access_rights = res.data["access_rights"]
    assert access_rights["rems_approval_type"] == "automatic"
    assert access_rights["data_access_application_instructions"] == {"en": "This is how you apply"}
    assert access_rights["data_access_terms"] == {"en": "Terms here", "fi": "Käyttöehdot tähän"}
    assert access_rights["data_access_reviewer_instructions"] == {"en": "plz review"}

    # Non-editor user should not see the reviewer instructions
    res = user_client.get(f"/v3/datasets/{dataset.id}", content_type="application/json")
    access_rights = res.data["access_rights"]
    assert "rems_approval_type" in access_rights
    assert "data_access_application_instructions" in access_rights
    assert "data_access_terms" in access_rights
    assert "data_access_reviewer_instructions" not in access_rights

    # Terms should be converted into a license in created REMS resource
    assert len(mock_rems.entities["resource"]) == 1
    terms_license = mock_rems.entities["resource"][1]["licenses"][0]
    assert terms_license["localizations"] == {
        "en": {"title": "Terms for data access", "textcontent": "Terms here"},
        "fi": {"title": "Käyttöluvan ehdot", "textcontent": "Käyttöehdot tähän"},
    }

    license_entity = REMSLicense.objects.get(key=f"dataset-{dataset.id}-access-terms")
    assert license_entity.custom_license_dataset == dataset


def test_publish_rems_dataset_error(
    mock_rems, admin_client, rems_dataset_json, data_catalog, reference_data, requests_mock
):
    requests_mock.post(
        f"{settings.REMS_BASE_URL}/api/catalogue-items/create",
        status_code=500,
        json="this failed",
    )
    res = admin_client.post("/v3/datasets", rems_dataset_json, content_type="application/json")
    assert res.status_code == 201
    assert REMSCatalogueItem.objects.filter(key=f"dataset-{res.data['id']}").count() == 0
    dataset = Dataset.objects.get(id=res.data["id"])
    assert "this failed" in dataset.rems_publish_error
    assert dataset.rems_status == REMSStatus.ERROR
    assert dataset.rems_id is None


def test_rems_applications(mock_rems, user_client):
    dataset = factories.REMSDatasetFactory()
    REMSService().publish_dataset(dataset)

    # Create application
    res = user_client.post(
        f"/v3/datasets/{dataset.id}/rems-applications", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.json() == {"success": True}

    # Check application has been created for current user
    res = user_client.get(
        f"/v3/datasets/{dataset.id}/rems-applications", content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["application/applicant"]["userid"] == user_client._user.fairdata_username
    assert res.data[0]["application/resources"][0]["resource/ext-id"] == str(dataset.id)

    # Auto-approve is enabled, there should be an entitlement
    res = user_client.get(
        f"/v3/datasets/{dataset.id}/rems-entitlements", content_type="application/json"
    )
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["resource"] == str(dataset.id)
    assert res.data[0]["user"]["userid"] == user_client._user.fairdata_username


def test_dataset_rems_application_status(settings, mock_rems, admin_client, user_client):
    dataset = factories.REMSDatasetFactory()
    service = REMSService()

    # REMS disabled, so allowed_actions does not have REMS fields
    settings.REMS_ENABLED = False
    data = user_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"].get("rems_status") is None
    assert dataset.get_user_rems_application_status(user_client._user) == "disabled"

    # Admin does not have fairdata_username so is not a REMS user
    settings.REMS_ENABLED = True
    data = admin_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"]["rems_status"] == "not_rems_user"

    # Dataset not enabled for REMS or not published to REMS yet
    data = user_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"]["rems_status"] == "not_in_rems"

    # Dataset in REMS, user has not made an application yet
    service.publish_dataset(dataset)
    data = user_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"]["rems_status"] == "no_application"

    # Application created and submitted with auto-approve workflow
    service.create_application_for_dataset(user_client._user, dataset)
    data = user_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"]["rems_status"] == "approved"

    # Application approved but no entitlement found -> needs new application
    mock_rems.entities["entitlement"].clear()  # Remove all entitlements
    data = user_client.get(f"/v3/datasets/{dataset.id}?include_allowed_actions=true").json()
    assert data["allowed_actions"]["rems_status"] == "no_application"


def test_dataset_rems_application_data(
    settings, mock_rems, admin_client, user_client, license_reference_data
):
    dataset = factories.REMSDatasetFactory(
        access_rights__data_access_terms={"en": "Terms here", "fi": "Ehdot tässä"}
    )
    ref_lic = factories.DatasetLicenseFactory(
        reference=License.objects.get(
            url="http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0"
        )
    )
    custom_lic = factories.DatasetLicenseFactory(
        title={"en": "License name", "fi": "Lisenssin nimi"}, custom_url="https://license.url"
    )
    dataset.access_rights.license.set([ref_lic, custom_lic])
    service = REMSService()
    service.publish_dataset(dataset)

    data = user_client.get(f"/v3/datasets/{dataset.id}/rems-application-data").json()
    assert data == {
        "licenses": [
            {
                "id": 1,
                "licensetype": "text",
                "localizations": {
                    "en": {
                        "textcontent": "Terms here",
                        "title": "Terms for data access",
                    },
                    "fi": {
                        "textcontent": "Ehdot tässä",
                        "title": "Käyttöluvan ehdot",
                    },
                },
                "is_data_access_terms": True,
            },
            {
                "id": 2,
                "licensetype": "link",
                "localizations": {
                    "en": {
                        "textcontent": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                        "title": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                    },
                    "fi": {
                        "textcontent": "http://uri.suomi.fi/codelist/fairdata/license/code/CC-BY-4.0",
                        "title": "Creative Commons Nimeä 4.0 Kansainvälinen (CC BY 4.0)",
                    },
                },
                "is_data_access_terms": False,
            },
            {
                "id": 3,
                "licensetype": "link",
                "localizations": {
                    "en": {
                        "textcontent": "https://license.url",
                        "title": "License name",
                    },
                    "fi": {
                        "textcontent": "https://license.url",
                        "title": "Lisenssin nimi",
                    },
                },
                "is_data_access_terms": False,
            },
        ],
        "forms": [],
    }
