import logging

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.contrib.auth import get_user_model

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
    etsin_pc_dc_json["publishing_channels"] = ["default", "etsin"]
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
    both_pc_dc_json["publishing_channels"] = ["default", "etsin", "ttv"]
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
    user_client, catalog_datasets, dataset_a_json, admin_client, user
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

    # Setting catalog should require dataset update permission in the catalog
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 403

    # Setting catalog should work after creation permission has been added
    dc = DataCatalog.objects.get(id="data-catalog-test")
    dc.dataset_groups_create.add(user.groups.first())
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 200, res.data

    # Patching dataset that is already in the catalog should require update permission
    dc.dataset_groups_create.remove(user.groups.first())
    res = user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"data_catalog": "data-catalog-test"},
        content_type="application/json",
    )
    assert res.status_code == 403


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


def test_catalog_datasets_update_requires_update_group(
    user_client,
    admin_org_user_client,
    fairdata_users_group,
    dataset_a_json,
    reference_data,
):
    """User with admin_organization permission needs update group to edit datasets."""
    from apps.users.factories import AdminOrganizationFactory

    # Catalog where fairdata users can create but not update datasets
    catalog = factories.DataCatalogFactory(
        id="data-catalog-update-test",
        allowed_pid_types=["URN", "DOI"],
    )
    catalog.dataset_groups_create.set([fairdata_users_group])
    catalog.dataset_groups_update.set([])
    catalog.save()

    # Create admin organization and dataset with admin_organization set
    AdminOrganizationFactory(id="test_org", pref_label={"en": "Test Organization"})
    dataset_payload = {
        **dataset_a_json,
        "data_catalog": catalog.id,
        "metadata_owner": {
            "user": "test_user",
            "organization": "test_organization",
            "admin_organization": "test_org",
        },
    }
    res = user_client.post("/v3/datasets", dataset_payload, content_type="application/json")
    assert res.status_code == 201
    dataset_id = res.data["id"]

    # admin_org_user has permission through admin_organization but should fail
    # because they are not in dataset_groups_update
    res = admin_org_user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"title": {"en": "Updated title"}},
        content_type="application/json",
    )
    assert res.status_code == 403

    # Add user's group to dataset_groups_update
    catalog.dataset_groups_update.add(fairdata_users_group)
    catalog.save()

    # Updating the dataset should now succeed
    res = admin_org_user_client.patch(
        f"/v3/datasets/{dataset_id}",
        {"description": {"en": "Updated description"}},
        content_type="application/json",
    )
    assert res.status_code == 200


def test_catalog_datasets_update_with_dataset_groups_update(
    user_client,
    admin_client,
    user,
    fairdata_users_group,
    dataset_a_json,
    reference_data,
):
    """User should be able to update datasets in catalogs where their group is in dataset_groups_update."""
    # Create first datacatalog with fairdata_users in dataset_groups_update
    catalog_with_update = factories.DataCatalogFactory(
        id="data-catalog-with-update",
        allowed_pid_types=["URN", "DOI"],
    )
    catalog_with_update.dataset_groups_create.set([fairdata_users_group])
    catalog_with_update.dataset_groups_update.set([fairdata_users_group])
    catalog_with_update.save()

    # Create second datacatalog without fairdata_users in dataset_groups_update
    catalog_without_update = factories.DataCatalogFactory(
        id="data-catalog-without-update",
        allowed_pid_types=["URN", "DOI"],
    )
    catalog_without_update.dataset_groups_create.set([fairdata_users_group])
    catalog_without_update.dataset_groups_update.set([])
    catalog_without_update.save()

    # Create dataset in first catalog (with dataset_groups_update)
    dataset_payload_1 = {
        **dataset_a_json,
        "data_catalog": catalog_with_update.id,
        "metadata_owner": {
            "user": user.username,
            "organization": "test_organization",
        },
    }
    res = user_client.post("/v3/datasets", dataset_payload_1, content_type="application/json")
    assert res.status_code == 201
    dataset_id_with_update = res.data["id"]

    # Create dataset in second catalog (without dataset_groups_update)
    dataset_payload_2 = {
        **dataset_a_json,
        "data_catalog": catalog_without_update.id,
        "metadata_owner": {
            "user": user.username,
            "organization": "test_organization",
        },
    }
    res = user_client.post("/v3/datasets", dataset_payload_2, content_type="application/json")
    assert res.status_code == 201
    dataset_id_without_update = res.data["id"]

    # Updating the dataset in catalog with dataset_groups_update should succeed
    res = user_client.patch(
        f"/v3/datasets/{dataset_id_with_update}",
        {"title": {"en": "Updated title"}},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Updating the dataset in catalog without dataset_groups_update should fail
    res = user_client.patch(
        f"/v3/datasets/{dataset_id_without_update}",
        {"title": {"en": "Updated title"}},
        content_type="application/json",
    )
    assert res.status_code == 403

    # Admin should be able to update the same dataset even without dataset_groups_update
    res = admin_client.patch(
        f"/v3/datasets/{dataset_id_without_update}",
        {"title": {"en": "Updated title"}},
        content_type="application/json",
    )
    assert res.status_code == 200

    # Superuser should also be able to update the same dataset even without dataset_groups_update
    MetaxUser = get_user_model()
    superuser = MetaxUser.objects.create_user(
        username="superuser_test",
        email="superuser@example.com",
        is_superuser=True,
    )
    superuser_client = Client()
    superuser_client.force_login(superuser)
    res = superuser_client.patch(
        f"/v3/datasets/{dataset_id_without_update}",
        {"title": {"en": "Updated title by superuser"}},
        content_type="application/json",
    )
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
        ("default", 1),
        ("etsin", 0),
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


def test_catalog_datasets_publishing_channels_pas(admin_client):
    factories.PublishedDatasetFactory(
        data_catalog__id="urn:nbn:fi:att:data-catalog-pas",
        preservation=factories.PreservationFactory(pas_package_created=True),
    )
    factories.PublishedDatasetFactory(
        data_catalog__id="urn:nbn:fi:att:data-catalog-pas",
        preservation=factories.PreservationFactory(pas_package_created=False),
    )

    res = admin_client.get("/v3/datasets")
    assert res.data["count"] == 2  # All published PAS datasets

    res = admin_client.get("/v3/datasets?publishing_channels=etsin")
    assert res.data["count"] == 1  # Only published PAS datasets with package created

    res = admin_client.get("/v3/datasets?publishing_channels=ttv")
    assert res.data["count"] == 1  # Only published PAS datasets with package created


def test_catalog_datasets_publishing_channels_drafts(admin_client):
    factories.DatasetFactory(data_catalog__id="urn:nbn:fi:att:data-catalog-ida")
    factories.DatasetFactory(data_catalog__id="urn:nbn:fi:att:data-catalog-ida")
    factories.PublishedDatasetFactory(data_catalog__id="urn:nbn:fi:att:data-catalog-ida")

    res = admin_client.get("/v3/datasets")
    assert res.data["count"] == 3  # All datasets

    res = admin_client.get("/v3/datasets?publishing_channels=default")
    assert res.data["count"] == 3  # All datasets

    res = admin_client.get("/v3/datasets?publishing_channels=etsin")
    assert res.data["count"] == 1  # No drafts for etsin

    res = admin_client.get("/v3/datasets?publishing_channels=ttv")
    assert res.data["count"] == 1  # No drafts for ttv


def test_catalog_datasets_publishing_channels_qvain(
    admin_client, dataset_a_json, data_catalog_list_url, reference_data, datacatalog_a_json
):
    """Test that only datasets from datacatalogs with qvain in publishing_channels are returned."""
    # Create first datacatalog with qvain in publishing_channels
    qvain_dc_json = datacatalog_a_json.copy()
    qvain_dc_json["id"] = "qvain-pc-data-catalog"
    qvain_dc_json["publishing_channels"] = ["qvain"]
    res = admin_client.post(data_catalog_list_url, qvain_dc_json, content_type="application/json")
    assert res.status_code == 201

    # Create second datacatalog without qvain in publishing_channels
    non_qvain_dc_json = datacatalog_a_json.copy()
    non_qvain_dc_json["id"] = "non-qvain-pc-data-catalog"
    non_qvain_dc_json["publishing_channels"] = ["etsin", "ttv"]
    res = admin_client.post(
        data_catalog_list_url, non_qvain_dc_json, content_type="application/json"
    )
    assert res.status_code == 201

    # Create dataset in first datacatalog (with qvain)
    dataset_json_1 = dataset_a_json.copy()
    dataset_json_1["data_catalog"] = "qvain-pc-data-catalog"
    res = admin_client.post("/v3/datasets", dataset_json_1, content_type="application/json")
    assert res.status_code == 201
    qvain_dataset_id = res.json()["id"]

    # Create dataset in second datacatalog (without qvain)
    dataset_json_2 = dataset_a_json.copy()
    dataset_json_2["data_catalog"] = "non-qvain-pc-data-catalog"
    res = admin_client.post("/v3/datasets", dataset_json_2, content_type="application/json")
    assert res.status_code == 201
    non_qvain_dataset_id = res.json()["id"]

    # Test that only the dataset with qvain is returned
    res = admin_client.get("/v3/datasets?publishing_channels=qvain")
    assert res.status_code == 200
    assert res.json()["count"] == 1
    assert res.json()["results"][0]["id"] == qvain_dataset_id
    assert res.json()["results"][0]["id"] != non_qvain_dataset_id


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
