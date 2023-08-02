import pytest

from apps.core import factories as core_factories
from apps.files import factories as file_factories
from rest_framework.reverse import reverse

from apps.files.models import File


@pytest.fixture(scope="module")
def delete_project_url():
    return reverse("file-delete-project")


@pytest.fixture
def file_set(client):
    files = file_factories.create_project_with_files(
        file_paths=[
            "/dir/sub1/file1.csv",
            "/dir/a.txt",
            "/rootfile.txt",
        ],
        file_args={"*": {"byte_size": 1024}},
    )
    data_catalog = core_factories.DataCatalogFactory()
    dataset = core_factories.DatasetFactory(data_catalog=data_catalog)
    return core_factories.FileSetFactory(
        dataset=dataset, file_storage=files["file_storage"], files=files["files"].values()
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "flush, all_objects_count",
    [
        (False, 3),
        (True, 0),
    ],
)
def test_delete_files_by_project_id(
    client, file_set, delete_project_url, flush, all_objects_count
):
    assert file_set.total_files_count == 3
    res = client.post(
        delete_project_url,
        {
            "project_identifier": file_set.project_identifier,
            "storage_service": file_set.file_storage.storage_service,
            "flush": flush
        },
        content_type="application/json",
    )
    assert File.available_objects.all().count() == 0
    assert File.all_objects.all().count() == all_objects_count
    assert res.status_code == 200
