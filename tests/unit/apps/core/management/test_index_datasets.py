from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.factories import DatasetFactory, DatasetActorFactory
from apps.core.models.catalog_record.dataset_index import DatasetIndexEntry

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
]


def test_index_datasets(dataset_cache):
    dataset1 = DatasetFactory(access_rights=None)
    dataset2 = DatasetFactory(access_rights=None)
    dataset3 = DatasetFactory(access_rights=None)
    for dataset in [dataset1, dataset2, dataset3]:
        dataset.actors.set(
            [
                DatasetActorFactory(
                    organization__pref_label={"en": "Org"},
                    roles=["creator", "publisher"],
                    person=None,
                )
            ]
        )

    dataset1.actors.add(
        DatasetActorFactory(
            organization__pref_label={"en": "Contributor Org"}, roles=["contributor"]
        )
    )

    out = StringIO()
    err = StringIO()
    call_command("index_datasets", stdout=out, stderr=err)
    assert err.getvalue() == ""
    assert "3/3 datasets indexed" in out.getvalue()
    assert "unused entries deleted" not in out.getvalue()

    # All datasets have same creator org, no creator persons
    assert DatasetIndexEntry.objects.filter(language="en", key="creator").count() == 1
    creator_entry = DatasetIndexEntry.objects.get(language="en", key="creator", value="Org")
    assert creator_entry.datasets.count() == 3

    # Creator organization is also listed in organizations
    assert DatasetIndexEntry.objects.filter(language="en", key="organization").count() == 2
    org_entry = DatasetIndexEntry.objects.get(language="en", key="organization", value="Org")
    assert org_entry.datasets.count() == 3

    # Dataset 1 has an extra contributor org
    contributor_org_entry = DatasetIndexEntry.objects.get(
        language="en", key="organization", value="Contributor Org"
    )
    assert contributor_org_entry.datasets.count() == 1

    # Entries for datasets that are no longer in use should be deleted
    dataset1.delete()
    out = StringIO()
    err = StringIO()
    call_command("index_datasets", stdout=out, stderr=err)
    assert err.getvalue() == ""
    assert "2/2 datasets indexed" in out.getvalue()
    assert "unused entries deleted" in out.getvalue()

    assert DatasetIndexEntry.objects.filter(language="en", key="organization").count() == 1
    assert not DatasetIndexEntry.objects.filter(
        language="en", key="organization", value="Contributor Org"
    ).exists()
