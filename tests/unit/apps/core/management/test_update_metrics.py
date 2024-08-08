from io import StringIO
from uuid import UUID

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.core import factories
from apps.core.models import DatasetMetrics

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.management,
    pytest.mark.adapter,
]

metrics_json = {
    "views": {
        "ALL": {
            "total_views": 1346,
            "details_views": 1346,
            "data_views": 1346,
            "events_views": 1346,
            "maps_views": 1346,
        },
        "c955e904-e3dd-4d7e-99f1-3fed446f96d1": {
            "total_views": 100,
            "details_views": 40,
            "data_views": 30,
            "events_views": 20,
            "maps_views": 10,
        },
    },
    "downloads": {
        "ALL": {
            "total_requests": 1234,
            "total_successful": 1234,
            "total_failed": 1234,
            "package_successful": 1234,
            "package_failed": 1234,
            "complete_successful": 1234,
            "complete_failed": 1234,
            "partial_successful": 1234,
            "partial_failed": 1234,
            "file_successful": 1234,
            "file_failed": 1234,
        },
        "c955e904-e3dd-4d7e-99f1-3fed446f96d1": {
            "total_requests": 1,
            "total_successful": 2,
            "total_failed": 3,
            "package_successful": 4,
            "package_failed": 5,
            "complete_successful": 6,
            "complete_failed": 7,
            "partial_successful": 8,
            "partial_failed": 9,
            "file_successful": 10,
            "file_failed": 11,
        },
    },
}


def test_update_metrics_fetch(requests_mock):
    requests_mock.get(settings.METRICS_REPORT_URL, json=metrics_json)
    dataset = factories.PublishedDatasetFactory(id=UUID("c955e904-e3dd-4d7e-99f1-3fed446f96d1"))
    out = StringIO()
    err = StringIO()
    call_command(
        "update_metrics",
        stdout=out,
        stderr=err,
    )
    assert err.getvalue() == ""
    metrics = dataset.metrics
    assert metrics.views_total_views == 100
    assert metrics.views_details_views == 40
    assert metrics.views_data_views == 30
    assert metrics.views_events_views == 20
    assert metrics.views_maps_views == 10
    assert metrics.downloads_total_requests == 1
    assert metrics.downloads_total_successful == 2
    assert metrics.downloads_total_failed == 3
    assert metrics.downloads_package_successful == 4
    assert metrics.downloads_package_failed == 5
    assert metrics.downloads_complete_successful == 6
    assert metrics.downloads_complete_failed == 7
    assert metrics.downloads_partial_successful == 8
    assert metrics.downloads_partial_failed == 9
    assert metrics.downloads_file_successful == 10
    assert metrics.downloads_file_failed == 11


def test_update_metrics_fake():
    dataset = factories.PublishedDatasetFactory(id=UUID("c955e904-e3dd-4d7e-99f1-3fed446f96d1"))

    out = StringIO()
    err = StringIO()
    call_command(
        "update_metrics",
        fake_datasets=["c955e904-e3dd-4d7e-99f1-3fed446f96d1"],
        stdout=out,
        stderr=err,
    )
    assert err.getvalue() == ""
    metrics = dataset.metrics
    for field in DatasetMetrics.metrics_fields:
        assert getattr(metrics, field) > 0


def test_update_metrics_fake_dataset_not_found():
    dataset = factories.PublishedDatasetFactory(id=UUID("c955e904-e3dd-4d7e-99f1-3fed446f96d1"))

    out = StringIO()
    err = StringIO()
    call_command(
        "update_metrics",
        fake_datasets=["c955e904-e3dd-4d7e-99f1-999911112222"],
        stdout=out,
        stderr=err,
    )
    assert "Dataset not found: c955e904-e3dd-4d7e-99f1-999911112222" in err.getvalue()
    assert getattr(dataset, "metrics", None) is None
