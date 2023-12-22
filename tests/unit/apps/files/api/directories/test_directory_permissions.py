import pytest

from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def project_user(file_tree):
    user, created = MetaxUser.objects.get_or_create(
        username="test_project_user",
        first_name="Project User",
        last_name="Testaaja",
        is_hidden=False,
        ida_projects=[file_tree["storage"].csc_project],
    )
    return user


@pytest.fixture
def project_client(client, project_user):
    client.force_login(project_user)
    return client


def test_directory_permissions_project_user(project_client, file_tree):
    res = project_client.get(
        "/v3/directories",
        {
            "storage_service": file_tree["storage"].storage_service,
            "csc_project": file_tree["storage"].csc_project,
        },
    )
    assert res.data["count"] == 4


def test_directory_permissions_dataset_anon_nonpublic(client, dataset_with_files):
    dataset_with_files.state = "draft"
    dataset_with_files.save()
    res = client.get(
        "/v3/directories",
        {
            "dataset": dataset_with_files.id,
            "storage_service": dataset_with_files.file_set.storage.storage_service,
            "csc_project": dataset_with_files.file_set.storage.csc_project,
        },
    )
    assert res.status_code == 403


@pytest.mark.xfail(
    reason="DatasetAccessPolicy.scope_queryset does not work correctly for anonymous users"
)
def test_directory_permissions_dataset_anon_published(client, dataset_with_files):
    dataset_with_files.state = "published"
    dataset_with_files.save()
    res = client.get(
        "/v3/directories",
        {
            "dataset": dataset_with_files.id,
            "storage_service": dataset_with_files.file_set.storage.storage_service,
            "csc_project": dataset_with_files.file_set.storage.csc_project,
        },
    )
    assert res.status_code == 200
    assert res.data["count"] == 2


def test_directory_permissions_dataset_noncreator_published(user_client, dataset_with_files):
    dataset_with_files.state = "published"
    dataset_with_files.save()
    res = user_client.get(
        "/v3/directories",
        {
            "dataset": dataset_with_files.id,
            "storage_service": dataset_with_files.file_set.storage.storage_service,
            "csc_project": dataset_with_files.file_set.storage.csc_project,
        },
    )
    assert res.status_code == 200
    assert res.data["count"] == 2
