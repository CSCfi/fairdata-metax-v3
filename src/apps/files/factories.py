from typing import Dict, List
from uuid import UUID, uuid4

import factory
from django.utils import timezone

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


def create_v2_file_data(projects: Dict[str, List[str]]) -> List[dict]:
    """Create V2 file list payload for testing migration logic.

    Example:
    ```
    create_v2_file_data({
        "ida:project_x": [
            "/data/file1",
            "/data/file2",
            "/data/file3",
        ],
    })
    ```
    will return three legacy files belonging to "project_x" in service "ida".
    """
    template = {
        "open_access": True,
        "date_created": "2020-07-16T18:20:14+03:00",
        "file_storage": {"identifier": "urn:nbn:fi:att:file-storage-<change-me>", "id": 1},
        "parent_directory": {"identifier": "<ignored-by-v3>", "id": 1},
        "file_frozen": "2021-04-12T12:23:45Z",
        "identifier": "<changeme>",
        "checksum": {
            "checked": "2021-04-12T12:23:45Z",
            "value": "12b23850ab29a9a43738dbad0279a872547cb9e7820dd36f0e07e906828b1ccc",
            "algorithm": "SHA-256",
        },
        "file_format": "<ignored-by-v3>",
        "removed": False,
        "file_uploaded": "2021-03-12T12:23:45Z",
        "file_modified": "2018-04-12T12:23:45Z",
        "pas_compatible": True,
        "byte_size": 1000,
        "file_name": "<ignored-by-v3>",
        "file_path": "<change-me>",
        "service_created": "ida",
        "project_identifier": "<change-me>",
        "user_created": "someuser@cscuserid",
        "id": 0,
    }

    files = []
    num = 0
    for project, paths in projects.items():
        storage, project_identifier = project.split(":")
        for path in paths:
            date_removed = None
            if path.startswith("-"):  # start path with - to remove file
                date_removed = "2022-01-03T12:13:14Z"
                path = path[1:]
            num += 1
            files.append(
                {
                    **template,
                    "file_path": path,
                    "file_storage": {"identifier": f"urn:nbn:fi:att:file-storage-{storage}"},
                    "id": num,
                    "identifier": str(UUID(int=num)),
                    "project_identifier": project_identifier,
                    "removed": bool(date_removed),
                    "date_removed": date_removed,
                }
            )
    return files
