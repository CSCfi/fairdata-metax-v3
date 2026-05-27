import logging

import pytest
from rest_framework import serializers
from tests.utils.utils import assert_nested_subdict

from apps.core import factories as core_factories
from apps.core.models import DataService
from apps.core.serializers import SpatialModelSerializer
from apps.files.factories import FileStorageFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def remote_dataset_json(dataset_a_json):
    dataset = {
        **dataset_a_json,
        "data_catalog": "urn:nbn:fi:att:data-catalog-att",
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
                "byte_size": 1024,
            }
        ],
    }
    return dataset


@pytest.fixture
def data_catalog_daas(fairdata_users_group, service_group):
    catalog = core_factories.DataCatalogFactory(
        id="urn:nbn:fi:att:data-catalog-daas",
        title={"en": "Dataset as a Service datasets", "fi": "Dataset as a Service-aineistot"},
        dataset_versioning_enabled=True,
        allow_remote_resources=True,
        allowed_pid_types=["DOI"],
        storage_services=[],
    )
    catalog.dataset_groups_create.set([fairdata_users_group, service_group])
    return catalog


def test_remote_resources(admin_client, remote_dataset_json, data_catalog_att, reference_data):
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201
    assert_nested_subdict(remote_dataset_json["remote_resources"], resp.json()["remote_resources"])


def test_remote_resources_not_allowed(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
    data_catalog_att.allow_remote_resources = False
    data_catalog_att.save()
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "does not allow remote resources" in resp.json()["remote_resources"]


def test_remote_resources_update(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
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
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
    del remote_dataset_json["remote_resources"][0]["title"]
    del remote_dataset_json["remote_resources"][0]["use_category"]
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "title" in resp.data["remote_resources"][0]
    assert "use_category" in resp.data["remote_resources"][0]


def test_remote_resources_invalid_media_type(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
    remote_dataset_json["remote_resources"][0]["mediatype"] = "kuvatiedosto"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "Value should contain a media type" in str(
        resp.data["remote_resources"][0]["mediatype"]
    )


def test_remote_resources_and_files(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
    FileStorageFactory(storage_service="ida", csc_project="project")
    remote_dataset_json["fileset"] = {"storage_service": "ida", "csc_project": "project"}
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert resp.json() == {
        "non_field_errors": "Cannot have files and remote resources in the same dataset."
    }


def test_remote_resources_checksum(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
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


def test_remote_resources_invalid_byte_size_type(
    admin_client, remote_dataset_json, data_catalog_att, reference_data
):
    remote_dataset_json["remote_resources"][0]["byte_size"] = "one-kilobyte"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "File size must be an integer number of bytes." in str(
        resp.data["remote_resources"][0]["byte_size"]
    )


def test_remote_resources_allow_file_paths_for_daas_catalog(
    admin_client, remote_dataset_json, data_catalog_daas, reference_data
):
    DataService.objects.create(
        id="LUMI-AIF",
        catalog=data_catalog_daas,
        pref_label={"fi": "LUMI-AIF", "en": "LUMI-AIF"},
    )
    remote_dataset_json["data_catalog"] = data_catalog_daas.id
    remote_dataset_json["generate_pid_on_publish"] = "DOI"
    remote_dataset_json["remote_resources"][0]["data_service"] = "LUMI-AIF"
    remote_dataset_json["remote_resources"][0]["access_url"] = "file:///path/to/resource/file.csv"
    remote_dataset_json["remote_resources"][0]["download_url"] = "file:///path/to/resource/file.csv"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 201, resp.data
    assert resp.data["remote_resources"][0]["access_url"] == "file:///path/to/resource/file.csv"
    assert resp.data["remote_resources"][0]["download_url"] == "file:///path/to/resource/file.csv"
    assert resp.data["remote_resources"][0]["data_service"] == "LUMI-AIF"


def test_remote_resources_reject_plain_file_paths_for_daas_catalog(
    admin_client, remote_dataset_json, data_catalog_daas, reference_data
):
    DataService.objects.create(
        id="LUMI-AIF",
        catalog=data_catalog_daas,
        pref_label={"fi": "LUMI-AIF", "en": "LUMI-AIF"},
    )
    remote_dataset_json["data_catalog"] = data_catalog_daas.id
    remote_dataset_json["generate_pid_on_publish"] = "DOI"
    remote_dataset_json["remote_resources"][0]["data_service"] = "LUMI-AIF"
    remote_dataset_json["remote_resources"][0]["access_url"] = "/path/to/resource/file.csv"
    remote_dataset_json["remote_resources"][0]["download_url"] = "/path/to/resource/file.csv"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert resp.data["remote_resources"][0]["access_url"] == [
        "Use file URL format for local paths, e.g. file:///home/torvinen/data.csv."
    ]
    assert resp.data["remote_resources"][0]["download_url"] == [
        "Use file URL format for local paths, e.g. file:///home/torvinen/data.csv."
    ]


def test_remote_resources_require_data_service_for_daas_catalog(
    admin_client, remote_dataset_json, data_catalog_daas, reference_data
):
    remote_dataset_json["data_catalog"] = data_catalog_daas.id
    remote_dataset_json["generate_pid_on_publish"] = "DOI"
    remote_dataset_json["remote_resources"][0]["access_url"] = "file:///path/to/resource/file.csv"
    remote_dataset_json["remote_resources"][0]["download_url"] = "file:///path/to/resource/file.csv"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "data_service" in resp.data["remote_resources"][0]


def test_remote_resources_data_service_must_belong_to_dataset_catalog(
    admin_client, remote_dataset_json, data_catalog_daas, data_catalog_att, reference_data
):
    DataService.objects.create(
        id="Allas",
        catalog=data_catalog_att,
        pref_label={"fi": "Allas", "en": "Allas"},
    )
    remote_dataset_json["data_catalog"] = data_catalog_daas.id
    remote_dataset_json["generate_pid_on_publish"] = "DOI"
    remote_dataset_json["remote_resources"][0]["data_service"] = "Allas"
    remote_dataset_json["remote_resources"][0]["access_url"] = "file:///path/to/resource/file.csv"
    remote_dataset_json["remote_resources"][0]["download_url"] = "file:///path/to/resource/file.csv"
    resp = admin_client.post("/v3/datasets", remote_dataset_json, content_type="application/json")
    assert resp.status_code == 400
    assert "data_service" in resp.data["remote_resources"][0]
