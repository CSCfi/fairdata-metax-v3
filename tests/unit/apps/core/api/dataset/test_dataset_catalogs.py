import json
import logging
from copy import deepcopy
from unittest.mock import ANY

import pytest
from django.contrib.auth.models import Group
from rest_framework.reverse import reverse
from tests.utils import assert_nested_subdict, matchers

from apps.core import factories
from apps.core.factories import DatasetFactory, MetadataProviderFactory
from apps.core.models import OtherIdentifier
from apps.core.models.catalog_record.dataset import Dataset
from apps.core.models.concepts import IdentifierType
from apps.files.factories import FileStorageFactory

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
