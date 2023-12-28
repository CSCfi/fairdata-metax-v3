from typing import Dict

import factory
from django.utils import timezone
from uuid import uuid4
from . import models


class FileStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileStorage
        django_get_or_create = ("csc_project", "storage_service")

    @factory.lazy_attribute
    def csc_project(self):
        model = models.FileStorage.get_proxy_model(self.storage_service)
        if "csc_project" not in model.required_extra_fields:
            return None
        return self.fallback_project

    class Params:
        fallback_project = factory.Faker("numerify", text="#######")

    storage_service = "ida"


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File
        django_get_or_create = ("directory_path", "filename", "storage")
        exclude = ("checksum_value",)
        skip_postgeneration_save = True

    id = factory.LazyFunction(uuid4)
    modified = factory.LazyFunction(timezone.now)
    pathname = factory.Faker("file_path")
    storage = factory.SubFactory(FileStorageFactory)
    size = factory.Faker("random_number")
    checksum_value = factory.Faker("md5")

    @factory.lazy_attribute
    def checksum(self):
        return f"md5:{self.checksum_value}"

    @factory.lazy_attribute
    def storage_identifier(self):
        return f"file_{self.filename}_{self.id}"

    @factory.lazy_attribute
    def directory_path(self):
        return self.pathname.rsplit("/", 1)[0] + "/"

    @factory.lazy_attribute
    def filename(self):
        return self.pathname.rsplit("/", 1)[1]

    @factory.post_generation
    def file_format(self, create, extracted, **kwargs):
        if not create:
            return

        self.filename = str(self.pathname).split("/")[-1]
        self.file_format = str(self.filename).split(".")[-1]
        self.save()


def create_file_tree(storage, file_paths, file_args={}) -> Dict[str, models.File]:
    """Add files to a project.

    Creates files in storage using list of file paths in file_paths.
    Optional file_args dict allows setting file factory arguments by file path.
    Use '*' as path to apply to all files.

    Returns dict of path->File mappings.
    """

    files = {
        path: FileFactory(
            storage=storage,
            pathname=path,
            **{**file_args.get("*", {}), **file_args.get(path, {})},
        )
        for path in file_paths
    }

    # The pre_save method for TimeStampedModel.modified prevents setting 'modified'
    # field in factory. Circumvent by using bulk_update.
    has_modified = False
    for file in files.values():
        record_modified = {
            **file_args.get("*", {}),
            **file_args.get(file.pathname, {}),
        }.get("record_modified")
        if record_modified:
            file.record_modified = record_modified
            has_modified = True
    if has_modified:
        models.File.all_objects.bulk_update(files.values(), ["record_modified"])
    return files


def create_project_with_files(*args, csc_project=None, storage_service=None, **kwargs) -> dict:
    """Create a storage project and add files to it.

    Passes arguments to create_file_tree.
    Returns dict with files and project parameters."""
    storage_args = {
        key: value
        for key, value in {
            "storage_service": storage_service,
            "csc_project": csc_project,
        }.items()
        if value is not None  # remove "None" values so defaults will be used instead
    }
    storage = FileStorageFactory(**storage_args)

    files = create_file_tree(
        storage=storage,
        *args,
        **kwargs,
    )
    return {
        "files": files,
        "storage": storage,
        "params": {
            "csc_project": storage.csc_project,
            "storage_service": storage.storage_service,
        },
    }
