import pytest

from apps.core import factories
from apps.files import factories as filefactories
from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def project_user(file_tree_a):
    user, created = MetaxUser.objects.get_or_create(
        username="test_project_user",
        first_name="Project User",
        last_name="Testaaja",
        is_hidden=False,
        csc_projects=[file_tree_a["storage"].csc_project],
    )
    return user


@pytest.fixture
def project_client(client, project_user):
    client.force_login(project_user)
    return client


@pytest.fixture
def dataset(file_tree_a):
    dataset = factories.DatasetFactory(persistent_identifier="somepid")
    dataset.actors.add(factories.DatasetActorFactory(roles=["creator", "publisher"]))
    factories.FileSetFactory(
        dataset=dataset,
        storage=file_tree_a["storage"],
        files=[
            file_tree_a["files"]["/dir/a.txt"],
            file_tree_a["files"]["/dir/b.txt"],
            file_tree_a["files"]["/dir/c.txt"],
        ],
    )
    return dataset


def test_files_get(admin_client, file_tree_a, file_tree_b):
    res = admin_client.get(
        "/v3/files",
        file_tree_a["params"],  # only files from file_tree_a
        content_type="application/json",
    )
    assert res.data["count"] == 16


def test_files_get_all(admin_client, file_tree_a, file_tree_b):
    res = admin_client.get(
        "/v3/files",  # files from both projects
        content_type="application/json",
    )
    assert res.data["count"] == 19


def test_files_get_anonymous(client, file_tree_a):
    """Anonymous user should not get any files without specifying dataset."""
    res = client.get(
        "/v3/files",
        content_type="application/json",
    )
    assert res.data["count"] == 0


def test_files_get_project_user(project_client, file_tree_b):
    """Project user should get all files from the project."""
    filefactories.create_project_with_files(
        file_paths=[
            "/filefromanotherproject.txt",
        ]
    )
    res = project_client.get(
        "/v3/files",
        content_type="application/json",
    )
    assert res.data["count"] == 16


def test_files_get_no_dataset(admin_client, file_tree_a):
    res = admin_client.get(
        "/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    # no dataset parameter, dataset_metadata should not be included
    assert "dataset_metadata" not in res.data["results"][0]


def test_files_get_dataset_files(admin_client, dataset):
    res = admin_client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()["results"]] == [
        "/dir/a.txt",
        "/dir/b.txt",
        "/dir/c.txt",
    ]


def test_files_get_dataset_files_anonymous_nonpublic(client, dataset):
    res = client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert res.data["count"] == 0


@pytest.mark.xfail(
    reason="DatasetAccessPolicy.scope_queryset does not work correctly for anonymous users"
)
def test_files_get_dataset_files_anonymous_published(client, dataset):
    dataset.publish()
    res = client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert res.data["count"] == 3


def test_files_get_dataset_files_non_owner_nonpublic(user_client, dataset):
    res = user_client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert res.data["count"] == 0


def test_files_get_dataset_files_non_owner_published(user_client, dataset):
    dataset.publish()
    res = user_client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert res.data["count"] == 3


def test_files_get_dataset_files_dataset_owner(user_client, user, dataset):
    dataset.metadata_owner.user = user
    dataset.metadata_owner.save()
    res = user_client.get(
        "/v3/files",
        {"dataset": dataset.id},
        content_type="application/json",
    )
    assert res.data["count"] == 3


def test_files_get_dataset_files_empty(admin_client, dataset):
    res = admin_client.get(
        "/v3/files",
        {"dataset": dataset.id, "csc_project": "pröject_does_not_exist"},
        content_type="application/json",
    )
    assert res.data["results"] == []


def test_files_get_multiple_storage_projects(admin_client, file_tree_a, file_tree_b):
    res = admin_client.get(
        "/v3/files",
        file_tree_a["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 16

    res = admin_client.get(
        "/v3/files",
        file_tree_b["params"],
        content_type="application/json",
    )
    assert res.json()["count"] == 3

    res = admin_client.get(
        "/v3/files",
        content_type="application/json",
    )
    assert res.json()["count"] == 19


def test_files_list_include_removed(admin_client, file_tree_a):
    file_tree_a["files"]["/dir/c.txt"].delete(soft=True)
    storage_identifier = file_tree_a["files"]["/dir/c.txt"].storage_identifier
    params = {
        **file_tree_a["params"],
        "pagination": False,
        "include_removed": False,
    }
    res = admin_client.get(
        "/v3/files",
        {**params, "storage_identifier": storage_identifier},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()] == []

    # also non-removed files should be included
    res = admin_client.get(
        "/v3/files",
        {**params, "storage_identifier": storage_identifier, "include_removed": True},
        content_type="application/json",
    )
    assert [f["pathname"] for f in res.json()] == [
        "/dir/c.txt",
    ]

    # also non-removed files should be included
    res = admin_client.get(
        "/v3/files",
        {**params, "pathname": "/dir/", "include_removed": True},
        content_type="application/json",
    )
    assert len(res.json()) == 15


def test_files_retrieve_include_removed(admin_client, file_tree_a):
    file_tree_a["files"]["/dir/c.txt"].delete(soft=True)
    file_id = file_tree_a["files"]["/dir/c.txt"].id
    params = {
        **file_tree_a["params"],
        "include_removed": False,
    }
    res = admin_client.get(
        f"/v3/files/{file_id}",
        params,
        content_type="application/json",
    )
    assert res.status_code == 404

    res = admin_client.get(
        f"/v3/files/{file_id}",
        {**params, "include_removed": True},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["pathname"] == "/dir/c.txt"

    # also non-removed files should be included
    file_b_id = file_tree_a["files"]["/dir/b.txt"].id
    res = admin_client.get(
        f"/v3/files/{file_b_id}",
        {**params, "include_removed": True},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.json()["pathname"] == "/dir/b.txt"


def test_files_list_invalid_storage_service(admin_client, file_tree_a):
    res = admin_client.get(
        "/v3/files?storage_service=doesnotexist",
        content_type="application/json",
    )
    assert res.status_code == 400
    assert "'doesnotexist' is not a valid choice. Valid choices are" in str(
        res.data["storage_service"]
    )


# new dataset
# existing dataset
# remove dataset *
# remove files from dataset using dataset api *
# add files
# remove files directly *
# ?delete files?

# *test also with files in other dataset
