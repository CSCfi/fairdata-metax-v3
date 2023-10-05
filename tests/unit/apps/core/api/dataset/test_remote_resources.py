import logging

import pytest
from rest_framework import serializers
from tests.utils.utils import assert_nested_subdict

from apps.core.serializers import SpatialModelSerializer

logger = logging.getLogger(__name__)


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


def test_remote_resources(client, remote_dataset_json, data_catalog, reference_data):
    resp = client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201
    assert_nested_subdict(remote_dataset_json["remote_resources"], resp.json()["remote_resources"])


def test_remote_resources_update(client, remote_dataset_json, data_catalog, reference_data):
    resp = client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
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
    resp = client.patch(
        f"/v3/datasets/{resp.data['id']}", patch_json, content_type="application/json"
    )
    assert resp.status_code == 200
    assert_nested_subdict(patch_json["remote_resources"], resp.json()["remote_resources"])
    assert resp.data["remote_resources"][0].get("access_url") is None
    assert resp.data["remote_resources"][0].get("download_url") is None
    assert resp.data["remote_resources"][0].get("mediatype") is None


def test_remote_resources_missing_fields(
    client, remote_dataset_json, data_catalog, reference_data
):
    del remote_dataset_json["remote_resources"][0]["title"]
    del remote_dataset_json["remote_resources"][0]["use_category"]
    resp = client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "title" in resp.data["remote_resources"][0]
    assert "use_category" in resp.data["remote_resources"][0]


def test_remote_resources_invalid_media_type(
    client, remote_dataset_json, data_catalog, reference_data
):
    remote_dataset_json["remote_resources"][0]["mediatype"] = "kuvatiedosto"
    resp = client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "Value should contain a media type" in str(
        resp.data["remote_resources"][0]["mediatype"]
    )