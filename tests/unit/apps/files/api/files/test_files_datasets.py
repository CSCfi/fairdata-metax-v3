import pytest
from django.utils import timezone

from apps.common.profiling import count_queries
from apps.core import factories
from tests.utils import matchers

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def file_tree_with_datasets(file_tree_a):
    tree = file_tree_a
    dataset_a = factories.DatasetFactory()
    tree["dataset_a"] = dataset_a
    factories.FileSetFactory(
        dataset=dataset_a,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ],
    )

    dataset_b = factories.DatasetFactory()
    tree["dataset_b"] = dataset_b
    factories.FileSetFactory(
        dataset=dataset_b,
        storage=file_tree_a["storage"],
        files=[
            tree["files"]["/dir/b.txt"],
            tree["files"]["/dir/c.txt"],
        ],
    )

    dataset_c = factories.DatasetFactory()
    tree["dataset_c"] = dataset_c
    factories.FileSetFactory(
        dataset=dataset_c,
        storage=file_tree_a["storage"],
        files=[
            tree["files"]["/dir/c.txt"],
        ],
    )
    tree["dataset_d"] = factories.DatasetFactory()

    # Deprecated and removed datasets should be ignored by the /files/datasets endpont
    dataset_deprecated = factories.DatasetFactory(deprecated=timezone.now())
    factories.FileSetFactory(
        dataset=dataset_deprecated,
        storage=file_tree_a["storage"],
        files=[
            tree["files"]["/dir/d.txt"],
        ],
    )
    dataset_deleted = factories.DatasetFactory(removed=timezone.now())
    factories.FileSetFactory(
        dataset=dataset_deleted,
        storage=file_tree_a["storage"],
        files=[
            tree["files"]["/dir/d.txt"],
        ],
    )

    return tree


def test_files_datasets(admin_client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = admin_client.post(
        "/v3/files/datasets",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/b.txt"].id,  # dataset b
            tree["files"]["/dir/c.txt"].id,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].id,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert sorted(res.json()) == sorted(
        [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ]
    )


def test_files_datasets_fields(admin_client, file_tree_with_datasets):
    """Test listing dataset fields for files"""
    tree = file_tree_with_datasets
    tree["dataset_a"].title = {"en": "dataset a"}
    tree["dataset_a"].persistent_identifier = "pid-a"
    tree["dataset_a"].save()
    tree["dataset_b"].title = {"en": "dataset b"}
    tree["dataset_b"].persistent_identifier = "pid-b"
    tree["dataset_b"].preservation = factories.PreservationFactory(pas_process_running=True)
    tree["dataset_b"].save()

    res = admin_client.post(
        "/v3/files/datasets?fields=id,title,preservation,persistent_identifier",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/b.txt"].id,  # dataset b
        ],
        content_type="application/json",
    )
    assert res.status_code == 200, res.data

    data = res.json()
    assert len(data) == 2
    assert data[0] == {
        "id": str(tree["dataset_a"].id),
        "persistent_identifier": "pid-a",
        "title": {"en": "dataset a"},
    }
    assert data[1] == {
        "id": str(tree["dataset_b"].id),
        "persistent_identifier": "pid-b",
        "title": {"en": "dataset b"},
        "preservation": matchers.DictContaining({"pas_process_running": True}),
    }


def test_files_datasets_cache(admin_client, file_tree_with_datasets, dataset_cache):
    """Test that /files/datasets uses dataset cache when used with ?fields."""
    tree = file_tree_with_datasets
    assert dataset_cache.get(tree["dataset_a"].id) is None
    assert dataset_cache.get(tree["dataset_b"].id) is None

    with count_queries() as counts:
        res = admin_client.post(
            "/v3/files/datasets?fields=id,access_rights",
            [
                tree["files"]["/dir/a.txt"].id,  # dataset a
                tree["files"]["/dir/b.txt"].id,  # dataset b
            ],
            content_type="application/json",
        )
        assert res.status_code == 200, res.data
        data1 = res.json()

    # Datasets were not in cache yet AccessRight was queried
    assert counts["SQLCompiler"]["AccessRights"] == 1

    # Datasets are now in serializer cache
    assert dataset_cache.get(tree["dataset_a"].id)
    assert dataset_cache.get(tree["dataset_b"].id)

    with count_queries() as counts2:
        res = admin_client.post(
            "/v3/files/datasets?fields=id,access_rights",
            [
                tree["files"]["/dir/a.txt"].id,  # dataset a
                tree["files"]["/dir/b.txt"].id,  # dataset b
            ],
            content_type="application/json",
        )
        assert res.status_code == 200, res.data
        data2 = res.json()

    # Datasets were in cache, AccessRight is not queried
    assert counts2["SQLCompiler"]["AccessRights"] == 0
    assert data1 == data2


def test_files_datasets_fields_include_nulls(admin_client, file_tree_with_datasets, dataset_cache):
    """Dataset cache is not used when ?include_nulls=true."""
    tree = file_tree_with_datasets
    tree["dataset_a"].title = {"en": "dataset a"}
    tree["dataset_a"].persistent_identifier = "pid-a"
    tree["dataset_a"].save()

    res = admin_client.post(
        "/v3/files/datasets?fields=id,title,preservation,persistent_identifier&include_nulls=true",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
        ],
        content_type="application/json",
    )
    assert res.status_code == 200, res.data
    data = res.json()
    assert data == [
        {
            "id": str(tree["dataset_a"].id),
            "persistent_identifier": "pid-a",
            "title": {"en": "dataset a"},
            "preservation": None,
        }
    ]
    assert dataset_cache.get(tree["dataset_a"].id) is None  # Don't cache when using include_nulls


def test_files_datasets_fields_relations(admin_client, file_tree_with_datasets):
    """Test listing dataset fields per file."""
    tree = file_tree_with_datasets
    res = admin_client.post(
        "/v3/files/datasets?fields=id,title&relations=true",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/c.txt"].id,  # dataset a,b,c
        ],
        content_type="application/json",
    )
    assert res.status_code == 200, res.data
    data = res.json()
    assert data[str(tree["files"]["/dir/a.txt"].id)] == [
        {"id": str(tree["dataset_a"].id), "title": tree["dataset_a"].title}
    ]
    assert sorted(data[str(tree["files"]["/dir/c.txt"].id)], key=lambda d: d["id"]) == sorted(
        [
            {"id": str(tree["dataset_a"].id), "title": tree["dataset_a"].title},
            {"id": str(tree["dataset_b"].id), "title": tree["dataset_b"].title},
            {"id": str(tree["dataset_c"].id), "title": tree["dataset_c"].title},
        ],
        key=lambda d: d["id"],
    )


def test_files_datasets_for_service(admin_client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = admin_client.post(
        "/v3/files/datasets?storage_service=ida",
        [
            tree["files"]["/dir/a.txt"].storage_identifier,  # dataset a
            tree["files"]["/dir/b.txt"].storage_identifier,  # dataset b
            tree["files"]["/dir/c.txt"].storage_identifier,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].storage_identifier,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert sorted(res.json()) == sorted(
        [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ]
    )


def test_files_datasets_for_service_with_relations(admin_client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = admin_client.post(
        "/v3/files/datasets?storage_service=ida&relations=true",
        [
            tree["files"]["/dir/a.txt"].storage_identifier,  # dataset a
            tree["files"]["/dir/b.txt"].storage_identifier,  # dataset b
            tree["files"]["/dir/c.txt"].storage_identifier,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].storage_identifier,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    res.json()[str(tree["files"]["/dir/c.txt"].storage_identifier)].sort()
    expected_result = {
        tree["files"]["/dir/a.txt"].storage_identifier: [str(tree["dataset_a"].id)],
        tree["files"]["/dir/b.txt"].storage_identifier: [str(tree["dataset_b"].id)],
        tree["files"]["/dir/c.txt"].storage_identifier: [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ],
    }
    expected_result[tree["files"]["/dir/c.txt"].storage_identifier].sort()
    assert res.json() == expected_result


def test_files_datasets_for_different_service(admin_client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = admin_client.post(
        "/v3/files/datasets?storage_service=pas",
        [
            tree["files"]["/dir/a.txt"].storage_identifier,  # dataset a
            tree["files"]["/dir/b.txt"].storage_identifier,  # dataset b
            tree["files"]["/dir/c.txt"].storage_identifier,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].storage_identifier,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json() == []
