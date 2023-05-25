import pytest
from django.conf import settings as s
from rest_framework import serializers

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
            "project": "ProjectFileStorage",
            "ida": "IDAFileStorage",
        }
    )


def test_create_file_storage_basic():
    storage = FileStorage.objects.create(storage_service="basic")
    assert type(storage) == BasicFileStorage


def test_create_file_storage_basic_with_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="basic", project_identifier="x")


def test_create_file_storage_project():
    storage = FileStorage.objects.create(storage_service="project", project_identifier="x")
    assert type(storage) == ProjectFileStorage


def test_create_file_storage_project_without_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="project")


def test_create_file_storage_ida():
    storage = FileStorage.objects.create(storage_service="ida", project_identifier="x")
    assert type(storage) == IDAFileStorage


def test_create_file_storage_ida_without_project():
    with pytest.raises(ValueError):
        FileStorage.objects.create(storage_service="ida")


@pytest.fixture
def multiple_file_storages():
    FileStorage.objects.create(storage_service="ida", project_identifier="x")
    FileStorage.objects.create(storage_service="ida", project_identifier="y")
    FileStorage.objects.create(storage_service="project", project_identifier="x")
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
