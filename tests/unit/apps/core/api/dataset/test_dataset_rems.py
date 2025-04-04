import pytest
from django.conf import settings

from apps.core.models.catalog_record.dataset import Dataset, REMSStatus
from apps.rems.models import REMSCatalogueItem

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
