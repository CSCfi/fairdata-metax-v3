"""Tests for listing dataset files with /dataset/<id>/files endpoint."""

import pytest
from rest_framework.exceptions import ValidationError

from apps.core import factories
from apps.core.models import FileSetDirectoryMetadata, FileSetFileMetadata, UseCategory
from apps.core.models.catalog_record.related import FileSet
from apps.files.factories import FileFactory
from apps.files.models import FileCharacteristics, FileStorage

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_fileset_preservation_copy(dataset_with_files, use_category_reference_data):
    use_category = UseCategory.objects.get(
        url="http://uri.suomi.fi/codelist/fairdata/use_category/code/source"
    )

    orig: FileSet = dataset_with_files.file_set
    f = orig.files.first()
    f.legacy_id = 123  # legacy_id gets cleared when copying file to PAS storage
    f.characteristics = FileCharacteristics.objects.create(encoding="UTF-8")
    f.save()
    orig.files.count()

    FileSetFileMetadata.objects.create(
        file_set=orig,
        file_id=f.id,
        title="File title",
        description="File description",
        use_category=use_category_reference_data[0],
    )

    FileSetDirectoryMetadata.objects.create(
        file_set=orig,
        pathname="/dir1/",
        storage=orig.storage,
        title="File title",
        description="File description",
        use_category=use_category,
    )

    dataset = factories.DatasetFactory()
    copy = orig.create_preservation_copy(dataset)

    assert copy.storage.csc_project == orig.storage.csc_project
    assert copy.storage.storage_service == "pas"
    assert orig.storage.storage_service == "ida"
    assert FileCharacteristics.objects.count() == 2  # Characteristics should be copied

    # Check that copied files have same path, storage_identifier and characteristics
    copy_files = sorted(
        copy.files.values_list(
            "directory_path", "filename", "storage_identifier", "characteristics__encoding"
        )
    )
    orig_files = sorted(
        orig.files.values_list(
            "directory_path", "filename", "storage_identifier", "characteristics__encoding"
        )
    )
    assert copy_files == orig_files

    # Check that original and copied files use the correct storages
    assert set(copy.files.values_list("storage_id", flat=True)) == {copy.storage.id}
    assert set(orig.files.values_list("storage_id", flat=True)) == {orig.storage.id}

    # Check that legacy_id values are removed from copies
    assert orig.files.filter(legacy_id__isnull=False).exists()
    assert not copy.files.filter(legacy_id__isnull=False).exists()

    # Check that is_legacy_syncable is set to False for copies
    assert set(orig.files.values_list("is_legacy_syncable", flat=True)) == {True}
    assert set(copy.files.values_list("is_legacy_syncable", flat=True)) == {False}

    # Check file metadata is copied
    assert copy.file_metadata.count() == 1
    assert orig.file_metadata.count() == 1
    assert copy.file_metadata.first().file != orig.file_metadata.first().file
    assert copy.file_metadata.first().use_category == orig.file_metadata.first().use_category

    # Check directory metadata is copied
    assert copy.directory_metadata.count() == 1
    assert copy.directory_metadata.first().storage == copy.storage
    assert orig.directory_metadata.count() == 1
    assert orig.directory_metadata.first().storage == orig.storage
    assert (
        copy.directory_metadata.first().use_category
        == orig.directory_metadata.first().use_category
    )


def test_fileset_preservation_copy_reuse_existing(dataset_with_files):
    orig: FileSet = dataset_with_files.file_set
    dataset = factories.DatasetFactory()
    storage = FileStorage.objects.create(
        storage_service="pas", csc_project=orig.storage.csc_project
    )
    # File exists in PAS with same name, use old file
    FileFactory(
        storage=storage,
        storage_identifier=orig.files.first().storage_identifier,
        pathname=orig.files.first().pathname,
    )
    orig.create_preservation_copy(dataset)


@pytest.mark.parametrize(
    "expected_error,file_to_remove",
    [
        # Remove 'pas_compatible_file' from dataset
        (
            "The PAS compatible file ",
            "pas_compatible_file",
        ),
        # Remove 'non_pas_compatible_file' from dataset
        (
            "The non-PAS compatible file ",
            "non_pas_compatible_file"
        )
    ]
)
def test_fileset_preservation_copy_missing_pas_compatible_file(
        dataset_with_files, expected_error, file_to_remove):
    orig: FileSet = dataset_with_files.file_set
    dataset = factories.DatasetFactory()

    # Create PAS <-> non PAS compatible file relation
    pas_file = orig.files.first()
    non_pas_file = orig.files.last()

    non_pas_file.pas_compatible_file = pas_file
    non_pas_file.save()

    # Remove either of the two files from dataset before trying to copy it
    if file_to_remove == "pas_compatible_file":
        orig.files.remove(pas_file)
    elif file_to_remove == "non_pas_compatible_file":
        orig.files.remove(non_pas_file)

    # Dataset must have both files from every pair. If not, error will be raised.
    with pytest.raises(ValidationError) as exc:
        orig.create_preservation_copy(dataset)

    assert expected_error in str(exc.value.detail["detail"])


def test_fileset_preservation_copy_pas_compatible_link(dataset_with_files):
    orig: FileSet = dataset_with_files.file_set
    dataset = factories.DatasetFactory()

    # Create PAS <-> non PAS compatible file relation
    pas_file = orig.files.first()
    non_pas_file = orig.files.last()

    non_pas_file.pas_compatible_file = pas_file
    non_pas_file.save()

    orig.create_preservation_copy(dataset)

    # Ensure the files in the new preservation dataset have the same names
    # but different identifiers
    new_file_set: FileSet = dataset.file_set

    copy_pas_file = new_file_set.files.get(checksum=pas_file.checksum)
    copy_non_pas_file = new_file_set.files.get(checksum=non_pas_file.checksum)

    assert copy_pas_file.filename == pas_file.filename
    assert copy_non_pas_file.filename == non_pas_file.filename

    assert copy_non_pas_file.pas_compatible_file.id == copy_pas_file.id

    assert copy_pas_file.id != pas_file.id
    assert copy_non_pas_file.id != non_pas_file.id


def test_fileset_preservation_copy_conflict(dataset_with_files):
    orig: FileSet = dataset_with_files.file_set
    dataset = factories.DatasetFactory()
    storage = FileStorage.objects.create(
        storage_service="pas", csc_project=orig.storage.csc_project
    )
    # File exists in PAS with different name, error
    FileFactory(
        storage=storage,
        storage_identifier=orig.files.first().storage_identifier,
        pathname="/now/for/something/different.csv",
    )

    with pytest.raises(ValidationError) as ec:
        orig.create_preservation_copy(dataset)
    assert "already exists in PAS storage" in str(ec.value.detail["detail"])
