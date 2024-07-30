import pytest

from apps.files.models.file_storage import (
    BasicFileStorage,
    FileStorage,
    IDAFileStorage,
    ProjectFileStorage,
)


@pytest.fixture(autouse=True)
def file_storage_settings(settings):
    settings.STORAGE_SERVICE_FILE_STORAGES.clear()
    settings.STORAGE_SERVICE_FILE_STORAGES.update(
        {
            "basic": "BasicFileStorage",
            "csc_project": "ProjectFileStorage",
            "ida": "IDAFileStorage",
        }
    )


def test_create_file_storage_basic():
    storage = FileStorage.objects.create(storage_service="basic")
    assert isinstance(storage, BasicFileStorage)


def test_create_file_storage_basic_with_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="basic", csc_project="x")


def test_create_file_storage_project():
    storage = FileStorage.objects.create(storage_service="csc_project", csc_project="x")
    assert isinstance(storage, ProjectFileStorage)


def test_create_file_storage_project_without_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="csc_project")


def test_create_file_storage_ida():
    storage = FileStorage.objects.create(storage_service="ida", csc_project="x")
    assert isinstance(storage, IDAFileStorage)


def test_create_file_storage_ida_without_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="ida")


@pytest.fixture
def multiple_file_storages():
    FileStorage.objects.create(storage_service="ida", csc_project="x")
    FileStorage.objects.create(storage_service="ida", csc_project="y")
    FileStorage.objects.create(storage_service="csc_project", csc_project="x")
    FileStorage.objects.create(storage_service="basic")


@pytest.mark.django_db
def test_file_storages_list_all(multiple_file_storages):
    assert FileStorage.objects.count() == 4


@pytest.mark.django_db
def test_file_storages_list_basic(multiple_file_storages):
    assert BasicFileStorage.objects.count() == 1


@pytest.mark.django_db
def test_file_storages_list_project(multiple_file_storages):
    assert ProjectFileStorage.objects.count() == 3  # counts also IDAFileStorages


@pytest.mark.django_db
def test_file_storages_list_ida(multiple_file_storages):
    assert IDAFileStorage.objects.count() == 2
