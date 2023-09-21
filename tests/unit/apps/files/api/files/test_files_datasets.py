import pytest

from apps.core import factories


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
    return tree


@pytest.mark.django_db
def test_files_datasets(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
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
    print(res.json())
    assert sorted(res.json()) == sorted(
        [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ]
    )


@pytest.mark.django_db
def test_files_datasets_for_service(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
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


@pytest.mark.django_db
def test_files_datasets_for_service_with_relations(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
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
    assert res.json() == {
        tree["files"]["/dir/a.txt"].storage_identifier: [str(tree["dataset_a"].id)],
        tree["files"]["/dir/b.txt"].storage_identifier: [str(tree["dataset_b"].id)],
        tree["files"]["/dir/c.txt"].storage_identifier: [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ],
    }


@pytest.mark.django_db
def test_files_datasets_for_different_service(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
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
