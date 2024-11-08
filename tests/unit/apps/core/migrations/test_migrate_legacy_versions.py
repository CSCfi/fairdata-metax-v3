from uuid import UUID

from apps.core import factories
from apps.core.models import Dataset, DatasetVersions, LegacyDataset
from apps.core.models.legacy_versions import migrate_dataset_versions


def create_legacy_dataset(id, version_ids, draft_of=None, next_draft=None):
    dataset_json = {  # Include only fields required for versions
        "identifier": str(id),
        "dataset_version_set": [{"identifier": str(version)} for version in version_ids],
    }
    if draft_of:
        dataset_json["draft_of"] = {"identifier": draft_of}
    if next_draft:
        dataset_json["next_draft"] = {"identifier": next_draft}
    LegacyDataset.objects.create(id=id, dataset_json=dataset_json)
    return factories.DatasetFactory(id=id)


def test_migrate_legacy_dataset_versions():
    id_1 = UUID(int=1)
    id_2 = UUID(int=2)
    id_3 = UUID(int=3)
    id_other = UUID(int=0)
    create_legacy_dataset(id=id_1, version_ids=[id_2, id_3, id_1, id_other])
    create_legacy_dataset(id=id_2, version_ids=[id_2])
    create_legacy_dataset(id=id_3, version_ids=[id_3])

    migrate_dataset_versions()
    dataset1 = Dataset.objects.get(id=id_1)
    dataset2 = Dataset.objects.get(id=id_2)
    dataset3 = Dataset.objects.get(id=id_3)
    assert (
        dataset1.dataset_versions_id
        == dataset2.dataset_versions_id
        == dataset3.dataset_versions_id
    )
    assert dataset1.dataset_versions.legacy_versions == [id_other, id_1, id_2, id_3]
    assert DatasetVersions.objects.count() == 1


def test_migrate_legacy_dataset_versions_create_new():
    id_1 = UUID(int=1)
    id_2 = UUID(int=2)
    create_legacy_dataset(id=id_1, version_ids=[id_1, id_2])
    create_legacy_dataset(id=id_2, version_ids=[id_2])
    DatasetVersions.all_objects.all().delete()  # Clear existing DatasetVersions

    migrate_dataset_versions()
    dataset1 = Dataset.objects.get(id=UUID(int=1))
    dataset2 = Dataset.objects.get(id=UUID(int=2))
    assert dataset1.dataset_versions_id == dataset2.dataset_versions_id
    assert DatasetVersions.objects.count() == 1


def test_migrate_legacy_dataset_versions_create_disjoint():
    id_1 = UUID(int=1)
    id_2 = UUID(int=2)
    id_3 = UUID(int=3)
    create_legacy_dataset(id=id_1, version_ids=[id_1, id_3])
    create_legacy_dataset(id=id_2, version_ids=[id_2])

    migrate_dataset_versions()
    dataset1 = Dataset.objects.get(id=id_1)
    dataset2 = Dataset.objects.get(id=id_2)
    assert dataset1.dataset_versions_id != dataset2.dataset_versions_id
    assert DatasetVersions.objects.count() == 2


def test_migrate_legacy_dataset_versions_draft_of():
    id_1 = UUID(int=1)
    id_2 = UUID(int=2)
    orig = create_legacy_dataset(id=id_1, version_ids=[])
    draft = create_legacy_dataset(id=id_2, version_ids=[], draft_of=id_1)
    migrate_dataset_versions()

    orig.refresh_from_db()
    draft.refresh_from_db()
    assert orig.dataset_versions.legacy_versions == [id_1, id_2]
    assert orig.dataset_versions == draft.dataset_versions


def test_migrate_legacy_dataset_versions_next_draft():
    id_1 = UUID(int=1)
    id_2 = UUID(int=2)
    draft = create_legacy_dataset(id=id_2, version_ids=[])
    orig = create_legacy_dataset(id=id_1, version_ids=[], next_draft=id_2)
    migrate_dataset_versions()

    orig.refresh_from_db()
    draft.refresh_from_db()
    assert orig.dataset_versions.legacy_versions == [id_1, id_2]
    assert orig.dataset_versions == draft.dataset_versions
