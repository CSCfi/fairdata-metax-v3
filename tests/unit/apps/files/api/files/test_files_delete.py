import pytest
from rest_framework.reverse import reverse

from apps.core import factories as core_factories
from apps.files import factories as file_factories
from apps.files.models import File


@pytest.fixture
def file_set():
    ida_files = file_factories.create_project_with_files(
        project="project",
        storage_service="ida",
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/a.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )
    data_catalog = core_factories.DataCatalogFactory()
    dataset = core_factories.DatasetFactory(data_catalog=data_catalog)
    return core_factories.FileSetFactory(
        dataset=dataset, storage=ida_files["storage"], files=ida_files["files"].values()
    )


@pytest.fixture
def pas_files():
    file_factories.create_project_with_files(
        project="project",
        storage_service="pas",
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/a.txt",
            "/dir/b.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"size": 1024}},
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 3),
        (True, 0),
    ],
)
def test_delete_files_by_project_id(client, file_set, flush, all_objects_count):
    assert file_set.total_files_count == 3
    url = f'{reverse("file-list")}?flush={flush}&project={file_set.project}'
    res = client.delete(url)
    assert File.available_objects.all().count() == 0
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 7),
        (True, 0),
    ],
)
def test_delete_files_by_project_id_delete_multiple_storages(
    client, file_set, pas_files, flush, all_objects_count
):
    assert File.all_objects.count() == 7
    url = f'{reverse("file-list")}?flush={flush}&project={file_set.project}'
    res = client.delete(url)
    assert File.available_objects.all().count() == 0
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 7),
        (True, 4),
    ],
)
def test_delete_files_by_project_id_delete_single_storage(
    client, file_set, pas_files, flush, all_objects_count
):
    assert File.all_objects.count() == 7
    url = f'{reverse("file-list")}?flush={flush}&project={file_set.project}&storage_service={file_set.storage_service}'
    res = client.delete(url)
    assert File.available_objects.all().count() == 4
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200
