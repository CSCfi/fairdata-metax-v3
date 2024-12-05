import pytest
from rest_framework.reverse import reverse
from tests.utils import matchers

from apps.core import factories as core_factories
from apps.files import factories as file_factories
from apps.files.models import File

pytestmark = [pytest.mark.django_db, pytest.mark.file]


@pytest.fixture
def file_set():
    ida_files = file_factories.create_project_with_files(
        csc_project="project",
        storage_service="ida",
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/a.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )
    data_catalog = core_factories.DataCatalogFactory()
    dataset = core_factories.PublishedDatasetFactory(data_catalog=data_catalog)
    return core_factories.FileSetFactory(
        dataset=dataset, storage=ida_files["storage"], files=ida_files["files"].values()
    )


@pytest.fixture
def pas_files():
    file_factories.create_project_with_files(
        csc_project="project",
        storage_service="pas",
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/a.txt",
            "/dir/b.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )


@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 3),
        (True, 0),
    ],
)
def test_delete_files_by_project_id(admin_client, file_set, flush, all_objects_count):
    assert file_set.total_files_count == 3
    url = f'{reverse("file-list")}?flush={flush}&csc_project={file_set.csc_project}'
    res = admin_client.delete(url)
    assert File.available_objects.all().count() == 0
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200


@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 7),
        (True, 0),
    ],
)
def test_delete_files_by_project_id_delete_multiple_storages(
    admin_client, file_set, pas_files, flush, all_objects_count
):
    assert File.all_objects.count() == 7
    url = f'{reverse("file-list")}?flush={flush}&csc_project={file_set.csc_project}'
    res = admin_client.delete(url)
    assert File.available_objects.all().count() == 0
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200
    file_set.dataset.refresh_from_db()
    assert file_set.dataset.deprecated == matchers.DateTime()


@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 7),
        (True, 4),
    ],
)
def test_delete_files_by_project_id_delete_single_storage(
    admin_client, file_set, pas_files, flush, all_objects_count
):
    assert File.all_objects.count() == 7
    url = f'{reverse("file-list")}?flush={flush}&csc_project={file_set.csc_project}&storage_service={file_set.storage_service}'
    res = admin_client.delete(url)
    assert File.available_objects.all().count() == 4
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200
    file_set.dataset.refresh_from_db()
    assert file_set.dataset.deprecated == matchers.DateTime()


def test_delete_draft_files(admin_client):
    ida_files = file_factories.create_project_with_files(
        csc_project="project",
        storage_service="ida",
        file_paths=[
            "/dir/a.txt",
        ],
        file_args={"*": {"size": 1024}},
    )
    data_catalog = core_factories.DataCatalogFactory()
    dataset = core_factories.DatasetFactory(data_catalog=data_catalog)
    file_set = core_factories.FileSetFactory(
        dataset=dataset, storage=ida_files["storage"], files=ida_files["files"].values()
    )

    url = f'{reverse("file-list")}?csc_project={file_set.csc_project}&storage_service={file_set.storage_service}'
    res = admin_client.delete(url)
    assert res.status_code == 200
    file_set.dataset.refresh_from_db()
    assert file_set.dataset.deprecated is None


def test_delete_file_in_multiple_datasets(admin_client, file_set):
    draft_dataset = core_factories.DatasetFactory(data_catalog=file_set.dataset.data_catalog)
    core_factories.FileSetFactory(
        dataset=draft_dataset, storage=file_set.storage, files=file_set.files.all()
    )

    file_id = File.objects.filter(storage=file_set.storage).first().id
    url = reverse("file-detail", kwargs={"pk": file_id})
    res = admin_client.delete(url)
    assert res.status_code == 204
    file_set.dataset.refresh_from_db()
    assert file_set.dataset.file_set.files.count() == 2
    assert file_set.dataset.deprecated == matchers.DateTime()
    original_deprecated = file_set.dataset.deprecated

    # Draft should not be deprecated
    assert draft_dataset.file_set.files.count() == 2
    draft_dataset.refresh_from_db()
    assert draft_dataset.deprecated is None

    # Delete another file, deprecation date should not change
    file_id = File.objects.filter(storage=file_set.storage).first().id
    url = reverse("file-detail", kwargs={"pk": file_id})
    res = admin_client.delete(url)
    assert res.status_code == 204
    file_set.dataset.refresh_from_db()
    assert file_set.dataset.deprecated == original_deprecated


@pytest.mark.parametrize(
    "client,should_work", [("admin_client", True), ("pas_client", True), ("ida_client", False)]
)
def test_delete_files_pas_process_running(request, client, should_work, file_set):
    client = request.getfixturevalue(client)  # Select client fixture based on parameter
    file_set.files.filter(id__in=file_set.files.all()[:2]).update(pas_process_running=True)

    url = f'{reverse("file-list")}?csc_project={file_set.csc_project}&storage_service={file_set.storage_service}'
    res = client.delete(url, content_type="application/json")
    if should_work:
        assert res.status_code == 200
        assert res.data["count"] == 3
        assert file_set.files.count() == 0
    else:
        assert res.status_code == 423
        assert "2 locked files" in res.json()["detail"]
        assert file_set.files.count() == 3
