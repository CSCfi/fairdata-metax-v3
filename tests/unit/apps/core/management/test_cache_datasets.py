from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.factories import PublishedDatasetFactory
from apps.files.models import File

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.usefixtures("data_catalog", "reference_data", "v2_integration_settings"),
]


def test_cache_datasets(dataset_cache):
    datasets = [PublishedDatasetFactory(title={"en": f"title {i}"}) for i in range(10)]
    out = StringIO()
    err = StringIO()
    call_command("cache_datasets", stdout=out, stderr=err)
    assert len(err.getvalue()) == 0
    output = out.getvalue().strip().split("\n")
    assert output == [
        "Using LocMemCache cache backend",
        "Existing cached datasets: 0/10",
        "Caching 10 uncached datasets",
        "Prefetch complete",
        "Cached 10/10 datasets",
        "Cache ok",
    ]

    # Check that cache contains correct data
    assert dataset_cache.get(datasets[3].id)["title"] == {"en": "title 3"}
    assert dataset_cache.get(datasets[4].id)["title"] == {"en": "title 4"}

    # Some datasets are modified, their cached values should be invalid
    datasets[3].title = {"en": "new title 3"}
    datasets[3].save()
    datasets[4].save()

    # Cache only uncached datasets
    out = StringIO()
    err = StringIO()
    call_command("cache_datasets", stdout=out, stderr=err)
    assert len(err.getvalue()) == 0
    output = out.getvalue().strip().split("\n")
    assert output == [
        "Using LocMemCache cache backend",
        "Existing cached datasets: 8/10",
        "Caching 2 uncached datasets",
        "Prefetch complete",
        "Cached 2/2 datasets",
        "Cache ok",
    ]

    # Check that cache contains updated data
    assert dataset_cache.get(datasets[3].id)["title"] == {"en": "new title 3"}
    assert dataset_cache.get(datasets[4].id)["title"] == {"en": "title 4"}

    # Test clearing dataset cache
    assert len(dataset_cache._cache) == 10
    out = StringIO()
    err = StringIO()
    call_command("clear_dataset_cache", stdout=out, stderr=err)
    assert len(err.getvalue()) == 0
    output = out.getvalue().strip().split("\n")
    assert output == ["Cleared serialized_datasets cache"]

    # Verify that cached data is gone
    assert len(dataset_cache._cache) == 0
    assert dataset_cache.get(datasets[3].id) is None
    assert dataset_cache.get(datasets[4].id) is None


def test_cache_datasets_all(dataset_cache):
    _datasets = [PublishedDatasetFactory(title={"en": f"title {i}"}) for i in range(3)]
    call_command("cache_datasets")  # Datasets already in cache

    out = StringIO()
    err = StringIO()
    call_command("cache_datasets", stdout=out, stderr=err, all=True)
    assert len(err.getvalue()) == 0
    output = out.getvalue().strip().split("\n")
    assert output == [
        "Using LocMemCache cache backend",
        "Existing cached datasets: 3/3",
        "Caching all datasets",
        "Prefetch complete",
        "Cached 3/3 datasets",
        "Cache ok",
    ]


def test_cache_datasets_disabled():
    err = StringIO()
    call_command("cache_datasets", stderr=err)
    errors = err.getvalue().strip().split("\n")
    assert errors == ["The serialized_datasets cache is not enabled"]


def test_clear_dataset_cache_disabled():
    err = StringIO()
    call_command("clear_dataset_cache", stderr=err)
    errors = err.getvalue().strip().split("\n")
    assert errors == ["The serialized_datasets cache is not enabled"]
