from uuid import UUID

from apps.core.models import Dataset, DatasetVersions


def test_create_legacy_datasets_with_versions(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Datasets that are together in a dataset_version_set should be in the same DatasetVersions."""
    legacy_dataset_a_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert DatasetVersions.objects.count() == 1
    dataset_a_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    dataset_a = Dataset.objects.get(id=dataset_a_id)
    dataset_a_versions = dataset_a.dataset_versions_id

    # Add new dataset that has updated dataset_version_set
    legacy_dataset_b_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
        {"identifier": legacy_dataset_b_json["dataset_json"]["identifier"]},
        {"identifier": UUID(int=123)},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_b_id = legacy_dataset_b_json["dataset_json"]["identifier"]
    dataset_b = Dataset.objects.get(id=dataset_b_id)
    dataset_b_versions = dataset_b.dataset_versions_id
    assert dataset_a_versions == dataset_b_versions
    assert dataset_a.dataset_versions.legacy_versions == sorted(
        [
            UUID(legacy_dataset_a_json["dataset_json"]["identifier"]),
            UUID(legacy_dataset_b_json["dataset_json"]["identifier"]),
            UUID(int=123),
        ]
    )

    # Assert that version numbers are serialized correctly
    res_b = admin_client.get(f"/v3/datasets/{dataset_b_id}", content_type="application/json")
    dataset_versions_b = res_b.json()["dataset_versions"]
    assert dataset_versions_b[0]["version"] == 2
    assert dataset_versions_b[1]["version"] == 1

    res_a = admin_client.get(f"/v3/datasets/{dataset_a_id}", content_type="application/json")
    dataset_versions_a = res_a.json()["dataset_versions"]
    assert dataset_versions_a == dataset_versions_b


def test_create_legacy_datasets_with_versions_reverse(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Reversing Dataset insertion order should not affect resulting DatasetVersions."""
    legacy_dataset_b_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
        {"identifier": legacy_dataset_b_json["dataset_json"]["identifier"]},
        {"identifier": UUID(int=123)},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_b = Dataset.objects.get(id=legacy_dataset_b_json["dataset_json"]["identifier"])
    dataset_b_versions = dataset_b.dataset_versions_id

    # Insert dataset a that is missing dataset b from its dataset_version_set
    legacy_dataset_a_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_a = Dataset.objects.get(id=legacy_dataset_a_json["dataset_json"]["identifier"])
    dataset_a_versions = dataset_a.dataset_versions_id
    assert dataset_a_versions == dataset_b_versions
    assert dataset_a.dataset_versions.legacy_versions == sorted(
        [
            UUID(legacy_dataset_a_json["dataset_json"]["identifier"]),
            UUID(legacy_dataset_b_json["dataset_json"]["identifier"]),
            UUID(int=123),
        ]
    )


def test_create_legacy_datasets_with_versions_disjoint(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Datasets that are not together in a dataset_version_set should be in separate DatasetVersions."""
    legacy_dataset_a_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
        {"identifier": UUID(int=11)},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    dataset_a = Dataset.objects.get(id=legacy_dataset_a_json["dataset_json"]["identifier"])
    dataset_a_versions = dataset_a.dataset_versions_id

    legacy_dataset_b_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_b_json["dataset_json"]["identifier"]},
        {"identifier": UUID(int=22)},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 2
    dataset_b = Dataset.objects.get(id=legacy_dataset_b_json["dataset_json"]["identifier"])
    dataset_b_versions = dataset_b.dataset_versions_id
    assert dataset_a_versions != dataset_b_versions
    assert dataset_a.dataset_versions.legacy_versions == sorted(
        [
            UUID(legacy_dataset_a_json["dataset_json"]["identifier"]),
            UUID(int=11),
        ]
    )
    assert dataset_b.dataset_versions.legacy_versions == sorted(
        [
            UUID(legacy_dataset_b_json["dataset_json"]["identifier"]),
            UUID(int=22),
        ]
    )


def test_create_legacy_dataset_with_no_version_set(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Datasets should get a DatasetVersions even if it has no dataset_version_set."""
    legacy_dataset_a_json["dataset_json"]["dataset_version_set"] = None
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_a = Dataset.objects.get(id=legacy_dataset_a_json["dataset_json"]["identifier"])
    assert dataset_a.dataset_versions


def test_create_legacy_datasets_draft_of_versions(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Dataset in draft_of should belong to same dataset_versions."""
    legacy_dataset_a_json["dataset_json"]["dataset_version_set"] = [
        {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
    ]
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert DatasetVersions.objects.count() == 1
    dataset_a_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    dataset_a = Dataset.objects.get(id=dataset_a_id)

    # Add new dataset that has updated dataset_version_set
    legacy_dataset_b_json["dataset_json"].update(
        {
            "state": "draft",
            "dataset_version_set": [],
            "draft_of": {"identifier": dataset_a_id},
        }
    )
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_b_id = legacy_dataset_b_json["dataset_json"]["identifier"]
    dataset_b = Dataset.objects.get(id=dataset_b_id)
    assert dataset_a.dataset_versions == dataset_b.dataset_versions
    assert set(dataset_a.dataset_versions.legacy_versions) == {
        UUID(dataset_a_id),
        UUID(dataset_b_id),
    }


def test_create_legacy_datasets_next_draft_versions(
    admin_client,
    legacy_dataset_a_json,
    legacy_dataset_b_json,
    reference_data,
    data_catalog,
    data_catalog_att,
):
    """Dataset in next_draft should belong to same dataset_versions."""
    dataset_b_id = legacy_dataset_b_json["dataset_json"]["identifier"]
    legacy_dataset_a_json["dataset_json"].update(
        {
            "dataset_version_set": [
                {"identifier": legacy_dataset_a_json["dataset_json"]["identifier"]},
            ],
            "next_draft": {"identifier": dataset_b_id},
        }
    )
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_a_json, content_type="application/json"
    )
    assert res.status_code == 201, res.data
    assert DatasetVersions.objects.count() == 1
    dataset_a_id = legacy_dataset_a_json["dataset_json"]["identifier"]
    dataset_a = Dataset.objects.get(id=dataset_a_id)

    # next_draft should be added to legacy_versions even when it is not in dataset_version_set
    assert set(dataset_a.dataset_versions.legacy_versions) == {
        UUID(dataset_a_id),
        UUID(dataset_b_id),
    }

    # Check that next_draft actually gets the same dataset_versions
    legacy_dataset_b_json["dataset_json"]["state"] = "draft"
    legacy_dataset_b_json["dataset_json"]["dataset_version_set"] = []
    res = admin_client.post(
        "/v3/migrated-datasets", legacy_dataset_b_json, content_type="application/json"
    )
    assert res.status_code == 201
    assert DatasetVersions.objects.count() == 1
    dataset_b_id = legacy_dataset_b_json["dataset_json"]["identifier"]
    dataset_b = Dataset.objects.get(id=dataset_b_id)
    assert dataset_a.dataset_versions == dataset_b.dataset_versions
