import logging

import pytest
from tests.utils.utils import assert_nested_subdict

from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def remote_dataset_json(dataset_a_json):
    dataset = {
        **dataset_a_json,
        "remote_resources": [
            {
                "title": {"en": "Remote Resource"},
                "access_url": "https://access.url",
                "download_url": "https://download.url",
                "use_category": {
                    "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
                },
                "file_type": {"url": "http://uri.suomi.fi/codelist/fairdata/file_type/code/video"},
                "checksum": "md5:f00f",
                "mediatype": "text/csv",
            }
        ],
    }
    return dataset


def test_remote_resources(admin_client, remote_dataset_json, data_catalog, reference_data):
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201
    assert_nested_subdict(remote_dataset_json["remote_resources"], resp.json()["remote_resources"])


def test_remote_resources_not_allowed(
    admin_client, remote_dataset_json, data_catalog, reference_data
):
    data_catalog.allow_remote_resources = False
    data_catalog.save()
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "does not allow remote resources" in resp.json()["remote_resources"]


def test_remote_resources_update(admin_client, remote_dataset_json, data_catalog, reference_data):
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201
    patch_json = {
        "remote_resources": [
            {
                "title": {"en": "Replaced remote resource"},
                "use_category": {
                    "url": "http://uri.suomi.fi/codelist/fairdata/use_category/code/documentation"
                },
            }
        ]
    }
    resp = admin_client.patch(
        f"/v3/datasets/{resp.data['id']}", patch_json, content_type="application/json"
    )
    assert resp.status_code == 200
    assert_nested_subdict(patch_json["remote_resources"], resp.json()["remote_resources"])
    assert resp.data["remote_resources"][0].get("access_url") is None
    assert resp.data["remote_resources"][0].get("download_url") is None
    assert resp.data["remote_resources"][0].get("mediatype") is None


def test_remote_resources_missing_fields(
    admin_client, remote_dataset_json, data_catalog, reference_data
):
    del remote_dataset_json["remote_resources"][0]["title"]
    del remote_dataset_json["remote_resources"][0]["use_category"]
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "title" in resp.data["remote_resources"][0]
    assert "use_category" in resp.data["remote_resources"][0]


def test_remote_resources_invalid_media_type(
    admin_client, remote_dataset_json, data_catalog, reference_data
):
    remote_dataset_json["remote_resources"][0]["mediatype"] = "kuvatiedosto"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "Value should contain a media type" in str(
        resp.data["remote_resources"][0]["mediatype"]
    )


def test_remote_resources_and_files(
    admin_client, remote_dataset_json, data_catalog, reference_data
):
    FileStorageFactory(storage_service="ida", csc_project="project")
    remote_dataset_json["fileset"] = {"storage_service": "ida", "csc_project": "project"}
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert resp.json() == {
        "non_field_errors": "Cannot have files and remote resources in the same dataset."
    }


def test_remote_resources_checksum(
    admin_client, remote_dataset_json, data_catalog, reference_data
):
    remote_dataset_json["remote_resources"][0]["checksum"] = "sha1:12345fff"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201
    assert_nested_subdict(remote_dataset_json["remote_resources"], resp.json()["remote_resources"])

    remote_dataset_json["remote_resources"][0]["checksum"] = "other:12345fff"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201

    remote_dataset_json["remote_resources"][0]["checksum"] = "shzzhgfzh:12345fff"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
