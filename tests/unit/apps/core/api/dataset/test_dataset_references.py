import logging
import uuid

import pytest

from apps.core.factories import DatasetFactory, EntityRelationFactory, PublishedDatasetFactory
from apps.core.models import OtherIdentifier

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]

import uuid


def test_dataset_references(admin_client, subtests):
    referenced_dataset = PublishedDatasetFactory(
        id=uuid.UUID("00000000-0000-0000-0000-000000001337"),
        persistent_identifier="doi:10.23729/something",
        other_identifiers=[
            OtherIdentifier.objects.create(notation="doi:10.23729/other_doi"),
            OtherIdentifier.objects.create(notation="urn:someurn"),
        ],
    )

    related_ids = {
        "id": "00000000-0000-0000-0000-000000001337",
        "doi": "doi:10.23729/something",
        "doi_http": "http://doi.org/10.23729/something",
        "doi_https": "https://doi.org/10.23729/something",
        "other_doi": "doi:10.23729/other_doi",
        "other_urn": "urn:someurn",
    }
    related_datasets = {
        key: PublishedDatasetFactory(
            relation=[EntityRelationFactory(entity__entity_identifier=identifier)]
        )
        for key, identifier in related_ids.items()
    }
    draft = DatasetFactory(
        relation=[EntityRelationFactory(entity__entity_identifier="doi:10.23729/something")]
    )

    # Check all published datasets are listed in references
    resp = admin_client.get(
        f"/v3/datasets/{referenced_dataset.id}/references", content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.json()
    for key, dataset in related_datasets.items():
        with subtests.test(key):
            matches = [
                reference
                for reference in data
                if reference["referenced_by"]["id"] == str(dataset.id)
            ]
            assert len(matches) == 1
            match = matches[0]
            referenced_id = dataset.relation.first().entity.entity_identifier
            assert match["referenced_identifier"] == referenced_id
            assert match["referenced_by"]["title"] == dataset.title
            assert match["relation_type"]["pref_label"]["en"] == "Relation"

    with subtests.test("draft"):
        assert not any(
            reference for reference in data if reference["referenced_by"]["id"] == str(draft.id)
        )

def test_dataset_draft_references(admin_client):
    dataset = DatasetFactory(persistent_identifier=None)
    resp = admin_client.get(
        f"/v3/datasets/{dataset.id}/references", content_type="application/json"
    )
    assert resp.status_code == 200
    assert resp.json() == []