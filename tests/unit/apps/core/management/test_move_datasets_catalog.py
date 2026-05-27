from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core import factories
from apps.core.models.catalog_record.related import RemoteResource


pytestmark = [pytest.mark.django_db, pytest.mark.management]


def test_move_datasets_catalog_fails_if_any_dataset_missing():
    source = factories.DataCatalogFactory(id="urn:source", allow_remote_resources=True)
    target = factories.DataCatalogFactory(id="urn:target", allow_remote_resources=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=source)
    missing_id = "8ea7dd10-e29f-4f2f-ac03-9e8ff0f1ac6f"

    with pytest.raises(CommandError, match="Datasets not found"):
        call_command(
            "move_datasets_catalog",
            datasets=[str(dataset.id), missing_id],
            target=target.id,
        )

    dataset.refresh_from_db()
    assert dataset.data_catalog_id == source.id


def test_move_datasets_catalog_fails_whole_batch_if_any_dataset_invalid():
    source = factories.DataCatalogFactory(id="urn:source-batch", allow_remote_resources=True)
    target = factories.DataCatalogFactory(id="urn:target-batch", allow_remote_resources=False)
    use_category = factories.UseCategoryFactory()
    ok_dataset = factories.PublishedDatasetFactory(data_catalog=source)
    invalid_dataset = factories.PublishedDatasetFactory(data_catalog=source)
    RemoteResource.objects.create(
        dataset=invalid_dataset,
        title={"en": "remote"},
        use_category=use_category,
        access_url="https://example.com/data.csv",
    )

    with pytest.raises(CommandError, match="Validation failed"):
        call_command(
            "move_datasets_catalog",
            datasets=[str(ok_dataset.id), str(invalid_dataset.id)],
            target=target.id,
        )

    ok_dataset.refresh_from_db()
    invalid_dataset.refresh_from_db()
    assert ok_dataset.data_catalog_id == source.id
    assert invalid_dataset.data_catalog_id == source.id


def test_move_datasets_catalog_dry_run_validates_only():
    source = factories.DataCatalogFactory(id="urn:source-dry", allow_remote_resources=True)
    target = factories.DataCatalogFactory(id="urn:target-dry", allow_remote_resources=True)
    dataset = factories.PublishedDatasetFactory(data_catalog=source)
    out = StringIO()

    call_command(
        "move_datasets_catalog",
        datasets=[str(dataset.id)],
        target=target.id,
        dry=True,
        stdout=out,
    )

    dataset.refresh_from_db()
    assert dataset.data_catalog_id == source.id
    assert "Dry run successful" in out.getvalue()


def test_move_datasets_catalog_moves_all_when_valid():
    source = factories.DataCatalogFactory(id="urn:source-ok", allow_remote_resources=True)
    target = factories.DataCatalogFactory(id="urn:target-ok", allow_remote_resources=True)
    dataset_1 = factories.PublishedDatasetFactory(data_catalog=source)
    dataset_2 = factories.PublishedDatasetFactory(data_catalog=source)
    out = StringIO()

    call_command(
        "move_datasets_catalog",
        datasets=[str(dataset_1.id), str(dataset_2.id)],
        target=target.id,
        stdout=out,
    )

    dataset_1.refresh_from_db()
    dataset_2.refresh_from_db()
    assert dataset_1.data_catalog_id == target.id
    assert dataset_2.data_catalog_id == target.id
    assert "Moved 2 datasets" in out.getvalue()
