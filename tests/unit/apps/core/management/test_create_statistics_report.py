import ast

import pytest
from django.core.management import call_command

from apps.files.factories import FileFactory, FileStorageFactory
from apps.core.factories import (
    DatasetFactory,
    FileSetFactory,
    MetadataProviderFactory,
    PublishedDatasetFactory,
)
from apps.core.models import DataCatalog


def test_project_statistics_ida_dataset_with_multiple_files(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 3000
    assert stat["ida_count"] == 2
    assert len((stat["ida_published_datasets"])) == 1
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_multiple_ida_datasets_with_same_file(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset1 = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset1"}, data_catalog=data_catalog
    )
    dataset2 = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset2"}, data_catalog=data_catalog
    )
    files = [FileFactory(size=1000, storage=ida_storage)]
    file_set = FileSetFactory(dataset=dataset1, storage=ida_storage, files=files)
    file_set = FileSetFactory(dataset=dataset2, storage=ida_storage, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 1000
    assert stat["ida_count"] == 1
    assert len(stat["ida_published_datasets"]) == 2
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_ida_and_pas_dataset(
    admin_client, reference_data, data_catalog, test_user, contract, data_catalog_pas
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    preservation_object = {
        "preservation": {
            "contract": contract.id,
            "state": 0,
            "description": {"en": "Test preservation description"},
            "reason_description": "Test preservation reason description",
        }
    }

    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}", preservation_object, content_type="application/json"
    )
    assert res.status_code == 200

    res = admin_client.post(f"/v3/datasets/{dataset.id}/create-preservation-version")
    assert res.status_code == 201

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 1000
    assert stat["ida_count"] == 1
    assert len(stat["ida_published_datasets"]) == 1
    assert stat["pas_byte_size"] == 1000
    assert stat["pas_count"] == 1
    assert len(stat["pas_published_datasets"]) == 1
    assert stat["project_identifier"] == "project"


def test_project_statistics_removed_dataset(admin_client, reference_data, data_catalog, test_user):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    res = admin_client.delete(f"/v3/datasets/{dataset.id}")
    assert res.status_code == 204

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 0
    assert stat["ida_count"] == 0
    assert len(stat["ida_published_datasets"]) == 0
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_deprecated_dataset(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}",
        data={"deprecated": "2025-10-21T07:46:59Z"},
        content_type="application/json",
    )
    assert res.status_code == 200

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 3000
    assert stat["ida_count"] == 2
    assert len(stat["ida_published_datasets"]) == 1
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_draft_dataset(admin_client, reference_data, data_catalog, test_user):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = DatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 0
    assert stat["ida_count"] == 0
    assert len(stat["ida_published_datasets"]) == 0
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_new_versions(admin_client, reference_data, data_catalog, test_user):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    res = admin_client.post(
        f"/v3/datasets/{dataset.id}/new-version",
    )
    assert res.status_code == 201
    new_ds_id = res.json()["id"]

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 3000
    assert stat["ida_count"] == 2
    assert len(stat["ida_published_datasets"]) == 1
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"

    res = admin_client.patch(
        f"/v3/datasets/{new_ds_id}",
        data={"generate_pid_on_publish": "DOI"},
        content_type="application/json",
    )
    assert res.status_code == 200

    res = admin_client.post(f"/v3/datasets/{new_ds_id}/publish")
    assert res.status_code == 200

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 3000
    assert stat["ida_count"] == 2
    assert len(stat["ida_published_datasets"]) == 2
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_multiple_projects(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage1 = FileStorageFactory(storage_service="ida", csc_project="project1")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset1"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage1),
        FileFactory(size=2000, storage=ida_storage1),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage1, files=files)

    ida_storage2 = FileStorageFactory(storage_service="ida", csc_project="project2")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset2"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=3000, storage=ida_storage2),
        FileFactory(size=4000, storage=ida_storage2),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage2, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 2
    assert res.json()["results"][0]["project_identifier"] == "project1"
    assert res.json()["results"][1]["project_identifier"] == "project2"

    res = admin_client.get(f"/v3/statistics/project-statistics?projects=project2")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1
    assert res.json()["results"][0]["project_identifier"] == "project2"

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 7000
    assert stat["ida_count"] == 2
    assert len(stat["ida_published_datasets"]) == 1
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project2"


def test_project_statistics_published_and_unpublished_files(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    pub_files = [FileFactory(size=1000, storage=ida_storage)]
    FileFactory(size=2000, storage=ida_storage)  # file in same storage but not published
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=pub_files)

    call_command("create_statistic_report")

    res = admin_client.get("/v3/statistics/project-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][0]
    assert stat["ida_byte_size"] == 1000
    assert stat["ida_count"] == 1
    assert len(stat["ida_published_datasets"]) == 1
    assert stat["pas_byte_size"] == 0
    assert stat["pas_count"] == 0
    assert len(stat["pas_published_datasets"]) == 0
    assert stat["project_identifier"] == "project"


def test_project_statistics_post_not_allowed(admin_client):
    stat = {}
    stat["ida_byte_size"] = 0
    stat["ida_count"] = 0
    stat["ida_published_datasets"] = 0
    stat["pas_byte_size"] = 0
    stat["pas_count"] = 0
    stat["pas_published_datasets"] = 0
    stat["project_identifier"] = "project"

    res = admin_client.post(
        f"/v3/statistics/project-statistics", data=stat, content_type="application/json"
    )
    assert res.status_code == 405

    res = admin_client.get(f"/v3/statistics/project-statistics")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0


def test_organization_statistics_ida(admin_client, reference_data, data_catalog, test_user):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][3]
    assert stat["organization"] == "test-org"
    assert stat["byte_size_ida"] == 3000
    assert stat["byte_size_pas"] == 0
    assert stat["byte_size_total"] == 3000
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 1
    assert stat["count_other"] == 0
    assert stat["count_pas"] == 0
    assert stat["count_total"] == 1


def test_organization_statistics_removed_datasets(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    res = admin_client.delete(f"/v3/datasets/{dataset.id}")
    assert res.status_code == 204

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][3]
    assert stat["organization"] == "test-org"
    assert stat["byte_size_ida"] == 0
    assert stat["byte_size_pas"] == 0
    assert stat["byte_size_total"] == 0
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 0
    assert stat["count_other"] == 0
    assert stat["count_pas"] == 0
    assert stat["count_total"] == 0


def test_organization_statistics_with_deprecated_datasets(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}",
        data={"deprecated": "2025-10-21T07:46:59Z"},
        content_type="application/json",
    )
    assert res.status_code == 200

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][3]
    assert stat["organization"] == "test-org"
    assert stat["byte_size_ida"] == 3000
    assert stat["byte_size_pas"] == 0
    assert stat["byte_size_total"] == 3000
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 1
    assert stat["count_other"] == 0
    assert stat["count_pas"] == 0
    assert stat["count_total"] == 1


def test_organization_statistics_ida_and_pas_dataset(
    admin_client, reference_data, data_catalog, test_user, contract, data_catalog_pas
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    preservation_object = {
        "preservation": {
            "contract": contract.id,
            "state": 0,
            "description": {"en": "Test preservation description"},
            "reason_description": "Test preservation reason description",
        }
    }

    res = admin_client.patch(
        f"/v3/datasets/{dataset.id}", preservation_object, content_type="application/json"
    )
    assert res.status_code == 200

    res = admin_client.post(f"/v3/datasets/{dataset.id}/create-preservation-version")
    assert res.status_code == 201

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][3]
    assert stat["organization"] == "test-org"
    assert stat["byte_size_ida"] == 1000
    assert stat["byte_size_pas"] == 1000
    assert stat["byte_size_total"] == 2000
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 1
    assert stat["count_other"] == 0
    assert stat["count_pas"] == 1
    assert stat["count_total"] == 2


def test_organization_statistics_harvested_catalog(
    admin_client, reference_data, data_catalog_harvested, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    res = admin_client.get(f"/v3/data-catalogs/{data_catalog_harvested.id}")
    catalog_json = res.json()
    catalog_json["id"] = "urn:nbn:fi:att:data-catalog-harvest-kielipankki"
    res = admin_client.post("/v3/data-catalogs", catalog_json, content_type="application/json")
    harvested_catalog = DataCatalog.objects.filter(
        id="urn:nbn:fi:att:data-catalog-harvest-kielipankki"
    )[0]
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider,
        title={"en": "Test Dataset"},
        data_catalog=harvested_catalog,
    )

    call_command("create_statistic_report")

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200

    stat = res.json()["results"][1]
    assert stat["organization"] == "kielipankki.fi"
    assert stat["byte_size_ida"] == 0
    assert stat["byte_size_pas"] == 0
    assert stat["byte_size_total"] == 0
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 0
    assert stat["count_other"] == 1
    assert stat["count_pas"] == 0
    assert stat["count_total"] == 1


def test_organization_statistics_organization_query_param(
    admin_client, reference_data, data_catalog, test_user
):
    metadata_provider = MetadataProviderFactory(
        user=test_user, organization="test-org", admin_organization="test-admin-org"
    )
    ida_storage = FileStorageFactory(storage_service="ida", csc_project="project")
    dataset = PublishedDatasetFactory(
        metadata_owner=metadata_provider, title={"en": "Test Dataset"}, data_catalog=data_catalog
    )
    files = [
        FileFactory(size=1000, storage=ida_storage),
        FileFactory(size=2000, storage=ida_storage),
    ]
    file_set = FileSetFactory(dataset=dataset, storage=ida_storage, files=files)

    call_command("create_statistic_report")

    res = admin_client.get(
        f"/v3/statistics/organization-statistics?organizations=test-org,kielipankki.fi"
    )
    assert res.status_code == 200

    assert len(res.json()["results"]) == 2
    assert res.json()["results"][0]["organization"] == "kielipankki.fi"
    assert res.json()["results"][1]["organization"] == "test-org"

    stat = res.json()["results"][1]
    assert stat["organization"] == "test-org"
    assert stat["byte_size_ida"] == 3000
    assert stat["byte_size_pas"] == 0
    assert stat["byte_size_total"] == 3000
    assert stat["count_att"] == 0
    assert stat["count_ida"] == 1
    assert stat["count_other"] == 0
    assert stat["count_pas"] == 0
    assert stat["count_total"] == 1


def test_organization_statistics_post_not_allowed(admin_client):
    stat = {}
    stat["organization"] = "test-org2"
    stat["byte_size_ida"] = 3000
    stat["byte_size_pas"] = 0
    stat["byte_size_total"] = 300000
    stat["count_att"] = 0
    stat["count_ida"] = 1
    stat["count_other"] = 0
    stat["count_pas"] = 0
    stat["count_total"] = 1

    res = admin_client.post(
        f"/v3/statistics/organization-statistics", data=stat, content_type="application/json"
    )
    assert res.status_code == 405

    res = admin_client.get(f"/v3/statistics/organization-statistics")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0
