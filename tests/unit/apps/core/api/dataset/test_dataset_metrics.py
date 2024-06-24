import logging

import pytest

from apps.core import factories
from apps.core.models import DatasetMetrics

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


@pytest.mark.usefixtures("data_catalog", "reference_data")
def test_get_dataset_metrics(admin_client):
    dataset = factories.PublishedDatasetFactory()
    metrics = factories.DatasetMetricsFactory(dataset=dataset)
    res = admin_client.get(f"/v3/datasets/{dataset.id}", content_type="application/json")
    assert res.status_code == 200
    assert "metrics" not in res.data

    res = admin_client.get(
        f"/v3/datasets/{dataset.id}?include_metrics=true", content_type="application/json"
    )
    assert res.status_code == 200
    for field in DatasetMetrics.metrics_fields:
        assert res.data["metrics"][field] == getattr(metrics, field)
