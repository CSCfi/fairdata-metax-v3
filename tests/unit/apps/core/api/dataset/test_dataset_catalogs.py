import logging

import pytest
from django.contrib.auth.models import Group

from apps.core import factories
from apps.core.models import DataCatalog
from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.fixture
def catalog_datasets(reference_data):
    # Catalog allows fairdata users to create datasets and edit their own datasets
    ida_catalog = factories.DataCatalogFactory(
        id="data-catalog-ida", allowed_pid_types=["URN", "DOI"]
    )
    fairdata_users, _ = Group.objects.get_or_create(name="fairdata_users")
    ida_catalog.dataset_groups_create.set([fairdata_users])

    # Catalog allows test service to create and edit any datasets
    service_catalog = factories.DataCatalogFactory(
        id="data-catalog-test", allowed_pid_types=["URN", "DOI"]
    )
    service_group, _ = Group.objects.get_or_create(name="test")
    service_catalog.dataset_groups_create.set([service_group])
    service_catalog.dataset_groups_admin.set([service_group])

    factories.PublishedDatasetFactory(
        persistent_identifier="ida-public-dataset", data_catalog=ida_catalog
    )
    factories.DatasetFactory(persistent_identifier="ida-draft-dataset", data_catalog=ida_catalog)
    factories.PublishedDatasetFactory(
        persistent_identifier="test-public-dataset", data_catalog=service_catalog
    )
    factories.DatasetFactory(
        persistent_identifier="test-draft-dataset", data_catalog=service_catalog
    )


@pytest.fixture
def publishing_channel_catalogs(
    admin_client, data_catalog_list_url, reference_data, datacatalog_a_json
):
    # Catalog with no publishing channels
    no_pc_dc_json = datacatalog_a_json
    no_pc_dc_json["id"] = "no-pc-data-catalog"
    no_pc_dc_json["publishing_channels"] = []
    res = admin_client.post(data_catalog_list_url, no_pc_dc_json, content_type="application/json")
    assert res.status_code == 201

    # Catalog with etsin publishing channel
    etsin_pc_dc_json = datacatalog_a_json
    etsin_pc_dc_json["id"] = "etsin-pc-data-catalog"
    etsin_pc_dc_json["publishing_channels"] = ["etsin"]
    res = admin_client.post(
        data_catalog_list_url, etsin_pc_dc_json, content_type="application/json"
    )
    assert res.status_code == 201

    # Catalog with ttv publishing channels
    ttv_pc_dc_json = datacatalog_a_json
    ttv_pc_dc_json["id"] = "ttv-pc-data-catalog"
    ttv_pc_dc_json["publishing_channels"] = ["ttv"]
    res = admin_client.post(data_catalog_list_url, ttv_pc_dc_json, content_type="application/json")
    assert res.status_code == 201

    # Catalog with both publishing channels
    both_pc_dc_json = datacatalog_a_json
    both_pc_dc_json["id"] = "both-pc-data-catalog"
    both_pc_dc_json["publishing_channels"] = ["etsin", "ttv"]
    res = admin_client.post(
        data_catalog_list_url, both_pc_dc_json, content_type="application/json"
    )
    assert res.status_code == 201


# List datasets


def test_catalog_datasets_list_public(user_client, catalog_datasets):
    res = user_client.get("/v3/datasets?pagination=false")
    assert [d["persistent_identifier"] for d in res.data] == [
        "test-public-dataset",
        "ida-public-dataset",
    ]


def test_catalog_datasets_list_service(service_client, catalog_datasets):
    res = service_client.get("/v3/datasets?pagination=false")
    assert [d["persistent_identifier"] for d in res.data] == [
        "test-draft-dataset",
        "test-public-dataset",
        "ida-public-dataset",
    ]


def test_catalog_datasets_list_admin(admin_client, catalog_datasets):
    res = admin_client.get("/v3/datasets?pagination=false")
    assert [d["persistent_identifier"] for d in res.data] == [
        "test-draft-dataset",
        "test-public-dataset",
        "ida-draft-dataset",
        "ida-public-dataset",
    ]


# Create dataset


def test_catalog_datasets_create_fairdata(user_client, catalog_datasets, dataset_a_json):
    res = user_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-ida"},
        content_type="application/json",
    )
    assert res.status_code == 201

    res = user_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 403


def test_catalog_datasets_create_and_set_catalog_fairdata(
    user_client, catalog_datasets, dataset_a_json, admin_client
):
    # Create draft without catalog
    dataset_a_json["state"] = "draft"
    dataset_a_json["data_catalog"] = None
    res = user_client.post(
        "/v3/datasets",
        dataset_a_json,
        content_type="application/json",
    )
    assert res.status_code == 201
    dataset_id = res.data["id"]

    # Setting catalog should require dataset creation permission in the catalog
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 403

    # Setting catalog should work after creation permission has been added
    dc = DataCatalog.objects.get(id="data-catalog-test")
    dc.dataset_groups_create.add(Group.objects.get(name="fairdata_users"))
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Patching dataset that is already in the catalog should not require creation permission
    dc.dataset_groups_create.remove(Group.objects.get(name="fairdata_users"))
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 200


def test_catalog_datasets_create_service(service_client, catalog_datasets, dataset_a_json):
    res = service_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-ida"},
        content_type="application/json",
    )
    assert res.status_code == 403

    res = service_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 201


def test_catalog_datasets_create_admin(admin_client, catalog_datasets, dataset_a_json):
    res = admin_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-ida"},
        content_type="application/json",
    )
    assert res.status_code == 201

    res = admin_client.post(
        "/v3/datasets",
        {**dataset_a_json, "data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 201


# Update dataset


def test_catalog_datasets_update_fairdata(user_client, catalog_datasets, dataset_a_json):
    """Fairdata user should not be able to update datasets they don't own."""
    dataset_id = Dataset.objects.get(persistent_identifier="ida-public-dataset").id
    res = user_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 403

    dataset_id = Dataset.objects.get(persistent_identifier="test-public-dataset").id
    res = user_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 403


def test_catalog_datasets_update_service(service_client, catalog_datasets, dataset_a_json):
    """Service should be able to update all datasets in their catalogs."""
    dataset_id = Dataset.objects.get(persistent_identifier="ida-public-dataset").id
    res = service_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 403

    dataset_id = Dataset.objects.get(persistent_identifier="test-public-dataset").id
    res = service_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 200


def test_catalog_datasets_update_admin(admin_client, catalog_datasets, dataset_a_json):
    """Admin should be able to update all datasets in all catalogs."""
    dataset_id = Dataset.objects.get(persistent_identifier="ida-public-dataset").id
    res = admin_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 200

    dataset_id = Dataset.objects.get(persistent_identifier="test-public-dataset").id
    res = admin_client.patch(f"/v3/datasets/{dataset_id}", {}, content_type="application/json")
    assert res.status_code == 200


# Publishing Channels


@pytest.mark.parametrize(
    "dc_id,publishing_channels,expected_count",
    [
        ("no-pc-data-catalog", "etsin", 0),
        ("etsin-pc-data-catalog", "etsin", 1),
        ("ttv-pc-data-catalog", "etsin", 0),
        ("both-pc-data-catalog", "etsin", 1),
        ("no-pc-data-catalog", "ttv", 0),
        ("etsin-pc-data-catalog", "ttv", 0),
        ("ttv-pc-data-catalog", "ttv", 1),
        ("both-pc-data-catalog", "ttv", 1),
        ("no-pc-data-catalog", "all", 1),
        ("etsin-pc-data-catalog", "all", 1),
        ("ttv-pc-data-catalog", "all", 1),
        ("both-pc-data-catalog", "all", 1),
    ],
)
def test_catalog_datasets_publishing_channels(
    admin_client,
    dataset_a_json,
    publishing_channel_catalogs,
    dc_id,
    publishing_channels,
    expected_count,
):
    dataset_json = dataset_a_json
    dataset_json["data_catalog"] = dc_id
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201

    res = admin_client.get(f"/v3/datasets?publishing_channels={publishing_channels}")
    actual_count = res.json()["count"]
    assert (
        actual_count == expected_count
    ), f"data catalog id: {dc_id}, publishing_channels: {publishing_channels}, expected_count: {expected_count}, actual count: {actual_count}"


@pytest.mark.parametrize(
    "dc_id,expected_count",
    [
        ("no-pc-data-catalog", 0),
        ("etsin-pc-data-catalog", 1),
        ("ttv-pc-data-catalog", 0),
        ("both-pc-data-catalog", 1),
    ],
)
def test_catalog_datasets_default_publishing_channels(
    admin_client, dataset_a_json, publishing_channel_catalogs, dc_id, expected_count
):
    dataset_json = dataset_a_json
    dataset_json["data_catalog"] = dc_id
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201

    res = admin_client.get(f"/v3/datasets")
    actual_count = res.json()["count"]
    assert (
        actual_count == expected_count
    ), f"data catalog id: {dc_id}, expected_count: {expected_count}, actual count: {actual_count}"


def test_catalog_datasets_invalid_publishing_channels(
    admin_client, dataset_a_json, publishing_channel_catalogs
):
    dataset_json = dataset_a_json
    dataset_json["data_catalog"] = "both-pc-data-catalog"
    res = admin_client.post("/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201

    res = admin_client.get("/v3/datasets?publishing_channels=foo")
    assert res.status_code == 400
    assert "Value 'foo' is not a valid choice" in str(res.json())


def test_catalog_datasets_publishing_channels_single_dataset(
    admin_client, dataset_a_json, publishing_channel_catalogs
):
    dataset_json = dataset_a_json
    dataset_json["data_catalog"] = "no-pc-data-catalog"
    res = admin_client.post(f"/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201
    cr_id = res.json()["id"]

    res = admin_client.get(f"/v3/datasets/{cr_id}")
    assert res.status_code == 200
    assert res.json()["id"] == cr_id


@pytest.mark.parametrize(
    "publishing_channels,expected_count",
    [
        ("etsin", 1),
        ("ttv", 0),
        ("all", 1),
        (None, 1),
    ],
)
def test_get_datasets_without_catalog(
    admin_client, dataset_a_json, publishing_channel_catalogs, publishing_channels, expected_count
):
    dataset_json = dataset_a_json
    dataset_json.pop("data_catalog")
    dataset_json["state"] = "draft"
    res = admin_client.post(f"/v3/datasets", dataset_json, content_type="application/json")
    assert res.status_code == 201

    if publishing_channels:
        res = admin_client.get(f"/v3/datasets?publishing_channels={publishing_channels}")
    else:
        res = admin_client.get(f"/v3/datasets")

    actual_count = res.json()["count"]
    assert (
        actual_count == expected_count
    ), f"publishing_channels: {publishing_channels}, expected_count: {expected_count}, actual count: {actual_count}"


# Update catalog


def test_catalog_datasets_update_change_catalog(admin_client, data_catalog):
    """Admin should be able to update all datasets in all catalogs."""
    ida_catalog = factories.DataCatalogFactory(id="data-catalog-ida")
    att_catalog = factories.DataCatalogFactory(id="data-catalog-att")
    dataset = factories.DatasetFactory(data_catalog=None)

    # Add catalog to draft dataset
    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}",
        {"data_catalog": ida_catalog.id},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["data_catalog"] == ida_catalog.id

    # Patch same catalog again, should be ok
    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}",
        {"data_catalog": ida_catalog.id},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Patch another catalog, should be disallowed
    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}",
        {"data_catalog": att_catalog.id},
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "Cannot change data catalog" in res.data["data_catalog"]
