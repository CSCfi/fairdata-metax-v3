import pytest

from apps.core import factories


@pytest.fixture
def file_tree_with_datasets(file_tree_a):
    tree = file_tree_a
    dataset_a = factories.DatasetFactory()
    dataset_a.files.set(
        [
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ]
    )
    tree["dataset_a"] = dataset_a

    dataset_b = factories.DatasetFactory()
    dataset_b.files.set(
        [
            tree["files"]["/dir/b.txt"],
            tree["files"]["/dir/c.txt"],
        ]
    )
    tree["dataset_b"] = dataset_b

    dataset_c = factories.DatasetFactory()
    dataset_c.files.set(
        [
            tree["files"]["/dir/c.txt"],
        ]
    )
    tree["dataset_c"] = dataset_c

    tree["dataset_d"] = factories.DatasetFactory()
    return tree


@pytest.mark.django_db
def test_files_datasets_datasets_for_files(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
        "/rest/v3/files/datasets",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/b.txt"].id,  # dataset b
            tree["files"]["/dir/c.txt"].id,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].id,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json() == {
        tree["files"]["/dir/a.txt"].id: [str(tree["dataset_a"].id)],
        tree["files"]["/dir/b.txt"].id: [str(tree["dataset_b"].id)],
        tree["files"]["/dir/c.txt"].id: [
            str(tree["dataset_a"].id),
            str(tree["dataset_b"].id),
            str(tree["dataset_c"].id),
        ],
    }


@pytest.mark.django_db
def test_files_datasets_datasets_for_files_keysonly(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
        "/rest/v3/files/datasets?keys=files&keysonly=true",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/b.txt"].id,  # dataset b
            tree["files"]["/dir/c.txt"].id,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].id,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json() == [
        tree["files"]["/dir/a.txt"].id,
        tree["files"]["/dir/b.txt"].id,
        tree["files"]["/dir/c.txt"].id,
    ]


@pytest.mark.django_db
def test_files_datasets_files_for_datasets(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    id_a = str(tree["dataset_a"].id)
    id_b = str(tree["dataset_b"].id)
    id_c = str(tree["dataset_c"].id)
    id_d = str(tree["dataset_d"].id)
    res = client.post(
        "/rest/v3/files/datasets?keys=datasets",
        [id_a, id_b, id_c, id_d],
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert set(data[id_a]) == set(
        [
            tree["files"]["/dir/a.txt"].id,
            tree["files"]["/dir/c.txt"].id,
        ]
    )
    assert set(data[id_b]) == {
        tree["files"]["/dir/b.txt"].id,
        tree["files"]["/dir/c.txt"].id,
    }
    assert set(data[id_c]) == {tree["files"]["/dir/c.txt"].id}


@pytest.mark.django_db
def test_files_datasets_files_for_datasets_keysonly(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    id_a = str(tree["dataset_a"].id)
    id_b = str(tree["dataset_b"].id)
    id_c = str(tree["dataset_c"].id)
    id_d = str(tree["dataset_d"].id)
    res = client.post(
        "/rest/v3/files/datasets?keys=datasets&keysonly",
        [id_a, id_b, id_c, id_d],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert set(res.json()) == {id_a, id_b, id_c}
