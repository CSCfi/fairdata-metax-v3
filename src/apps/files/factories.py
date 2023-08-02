from typing import Dict

import factory
from django.utils import timezone

from . import models


class FileStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileStorage
        django_get_or_create = ("project_identifier", "storage_service")

    project_identifier = factory.Faker("numerify", text="#######")
    storage_service = "ida"


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File
        django_get_or_create = ("directory_path", "file_name", "file_storage")

    id = factory.Faker("uuid4")
    created = factory.LazyFunction(timezone.now)
    modified = factory.LazyFunction(timezone.now)
    date_uploaded = factory.LazyFunction(timezone.now)
    file_modified = factory.LazyFunction(timezone.now)
    file_path = factory.Faker("file_path")
    checksum_algorithm = "MD5"
    checksum_value = factory.Faker("md5")
    checksum_checked = factory.LazyFunction(timezone.now)
    file_storage = factory.SubFactory(FileStorageFactory)
    byte_size = factory.Faker("random_number")

    @factory.lazy_attribute
    def file_storage_identifier(self):
        return f"file_{self.file_name}_{self.id}"

    @factory.lazy_attribute
    def directory_path(self):
        return self.file_path.rsplit("/", 1)[0] + "/"

    @factory.lazy_attribute
    def file_name(self):
        return self.file_path.rsplit("/", 1)[1]

    @factory.post_generation
    def file_format(self, create, extracted, **kwargs):
        if not create:
            return

        self.file_name = str(self.file_path).split("/")[-1]
        self.file_format = str(self.file_name).split(".")[-1]


def create_file_tree(file_storage, file_paths, file_args={}) -> Dict[str, models.File]:
    """Add files to a project.

    Creates files in file_storage using list of file paths in file_paths.
    Optional file_args dict allows setting file factory arguments by file path.
    Use '*' as path to apply to all files.

    Returns dict of path->File mappings.
    """

    files = {
        path: FileFactory(
            file_storage=file_storage,
            file_path=path,
            **{**file_args.get("*", {}), **file_args.get(path, {})},
        )
        for path in file_paths
    }

    # The pre_save method for TimeStampedModel.modified prevents setting 'modified'
    # field in factory. Circumvent by using bulk_update.
    has_modified = False
    for file in files.values():
        modified = {
            **file_args.get("*", {}),
            **file_args.get(file.file_path, {}),
        }.get("modified")
        if modified:
            file.modified = modified
            has_modified = True
    if has_modified:
        models.File.all_objects.bulk_update(files.values(), ["modified"])
    return files


def create_project_with_files(
    *args, project_identifier=None, storage_service=None, **kwargs
) -> dict:
    """Create a storage project and add files to it.

    Passes arguments to create_file_tree.
    Returns dict with files and project parameters."""
    storage_args = {
        key: value
        for key, value in {
            "storage_service": storage_service,
            "project_identifier": project_identifier,
        }.items()
        if value is not None  # remove "None" values so defaults will be used instead
    }
    storage = FileStorageFactory(**storage_args)

    files = create_file_tree(
        file_storage=storage,
        *args,
        **kwargs,
    )
    return {
        "files": files,
        "file_storage": storage,
        "params": {
            "project_identifier": storage.project_identifier,
            "storage_service": storage.storage_service,
        },
    }
