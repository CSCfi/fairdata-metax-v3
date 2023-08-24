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
def test_files_datasets_datasets_for_files(client, file_tree_with_datasets):
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
        "/v3/files/datasets?keys=files&keysonly=true",
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
        "/v3/files/datasets?keys=datasets",
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
        "/v3/files/datasets?keys=datasets&keysonly=true",
        [id_a, id_b, id_c, id_d],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert set(res.json()) == {id_a, id_b, id_c}


@pytest.mark.django_db
def test_files_datasets_datasets_for_files_storage_identifier(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
        "/v3/files/datasets?file_id_type=storage_identifier&storage_service=ida",
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
def test_files_datasets_datasets_for_files_storage_identifier_no_storage_service(
    client, file_tree_with_datasets
):
    tree = file_tree_with_datasets
    res = client.post(
        "/v3/files/datasets?file_id_type=storage_identifier",
        [
            tree["files"]["/dir/a.txt"].id,  # dataset a
            tree["files"]["/dir/b.txt"].id,  # dataset b
            tree["files"]["/dir/c.txt"].id,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].id,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "storage_service is required" in res.data["non_field_errors"][0]


@pytest.mark.django_db
def test_files_datasets_files_for_datasets_storage_identifier(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    id_a = str(tree["dataset_a"].id)
    id_b = str(tree["dataset_b"].id)
    id_c = str(tree["dataset_c"].id)
    id_d = str(tree["dataset_d"].id)
    res = client.post(
        "/v3/files/datasets?keys=datasets&file_id_type=storage_identifier&storage_service=ida",
        [id_a, id_b, id_c, id_d],
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert set(data[id_a]) == set(
        [
            tree["files"]["/dir/a.txt"].storage_identifier,
            tree["files"]["/dir/c.txt"].storage_identifier,
        ]
    )
    assert set(data[id_b]) == {
        tree["files"]["/dir/b.txt"].storage_identifier,
        tree["files"]["/dir/c.txt"].storage_identifier,
    }
    assert set(data[id_c]) == {tree["files"]["/dir/c.txt"].storage_identifier}


@pytest.mark.django_db
def test_files_datasets_datasets_for_files_different_service(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
        "/v3/files/datasets?file_id_type=storage_identifier&storage_service=pas",
        [
            tree["files"]["/dir/a.txt"].storage_identifier,  # dataset a
            tree["files"]["/dir/b.txt"].storage_identifier,  # dataset b
            tree["files"]["/dir/c.txt"].storage_identifier,  # dataset a,b,c
            tree["files"]["/dir/d.txt"].storage_identifier,  # no dataset
        ],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data == {}


@pytest.mark.django_db
def test_files_datasets_files_for_datasets_different_service(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    id_a = str(tree["dataset_a"].id)
    id_b = str(tree["dataset_b"].id)
    id_c = str(tree["dataset_c"].id)
    id_d = str(tree["dataset_d"].id)
    res = client.post(
        "/v3/files/datasets?keys=datasets&storage_service=pas",
        [id_a, id_b, id_c, id_d],
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data == {}


@pytest.mark.django_db
def test_files_datasets_dataset_for_files_invalid_uuid(client, file_tree_with_datasets):
    tree = file_tree_with_datasets
    res = client.post(
        "/v3/files/datasets?keys=datasets",
        ["this is not a uuid"],
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "not a valid UUID" in res.data[0]
