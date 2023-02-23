import factory
from django.utils import timezone

from . import models


class FileStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FileStorage
        django_get_or_create = ("id",)

    id = factory.Sequence(lambda n: f"data-storage-{n}")


class StorageProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.StorageProject
        django_get_or_create = ("project_identifier", "file_storage")

    project_identifier = factory.Faker("numerify", text="#######")
    file_storage = factory.SubFactory(FileStorageFactory)


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.File
        django_get_or_create = ("directory_path", "file_name", "storage_project")

    id = factory.Faker("uuid4")
    created = factory.LazyFunction(timezone.now)
    modified = factory.LazyFunction(timezone.now)
    date_uploaded = factory.LazyFunction(timezone.now)
    file_modified = factory.LazyFunction(timezone.now)
    file_path = factory.Faker("file_path")
    checksum_algorithm = "MD5"
    checksum_value = factory.Faker("md5")
    checksum_checked = factory.LazyFunction(timezone.now)
    storage_project = factory.SubFactory(StorageProjectFactory)
    byte_size = factory.Faker("random_number")

    @factory.lazy_attribute
    def directory_path(self):
        return self.file_path.rsplit("/")[0] + "/"

    @factory.lazy_attribute
    def file_name(self):
        return self.file_path.rsplit("/")[1]

    @factory.post_generation
    def file_format(self, create, extracted, **kwargs):
        if not create:
            return

        self.file_name = str(self.file_path).split("/")[-1]
        self.file_format = str(self.file_name).split(".")[-1]


def create_file_tree(storage_project, file_paths, file_args={}) -> list:
    """Add files to a project.

    Creates files in storage_project using list of file paths in file_paths.
    Optional file_args dict allows setting file factory arguments by file path.
    Use '*' as path to apply to all files.

    Returns list of files."""

    files = {
        path: FileFactory(
            storage_project=storage_project,
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


def create_project_with_files(*args, project_identifier=None, file_storage=None, **kwargs) -> dict:
    """Create a storage project and add files to it.

    Passes arguments to create_file_tree.
    Returns dict with files and project parameters."""
    project_args = {
        key: value
        for key, value in {
            "file_storage__id": file_storage,
            "project_identifier": project_identifier,
        }.items()
        if value is not None  # remove "None" values so defaults will be used instead
    }
    project = StorageProjectFactory(**project_args)

    files = create_file_tree(
        storage_project=project,
        *args,
        **kwargs,
    )
    return {
        "files": files,
        "params": {
            "project_identifier": project.project_identifier,
            "file_storage": project.file_storage_id,
        },
    }
