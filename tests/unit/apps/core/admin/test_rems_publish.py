import pytest
from django.test import RequestFactory
from django.urls import reverse

from apps.core import factories
from apps.core.admin import DatasetAdmin, REMSStatusFilter
from apps.core.models.catalog_record.dataset import Dataset, REMSStatus
from apps.rems.rems_service import REMSService


@pytest.mark.django_db
def test_admin_dataset_list_publish_to_rems(admin_client, mock_rems):
    """Test DatasetAdmin.publish_to_rems admin action."""
    dataset = factories.REMSDatasetFactory()
    assert dataset.rems_status is REMSStatus.NOT_PUBLISHED
    change_url = reverse("admin:core_dataset_changelist")
    data = {"action": "publish_to_rems", "_selected_action": [dataset.id]}
    response = admin_client.post(change_url, data, follow=True)
    assert response.status_code == 200
    dataset.refresh_from_db()
    assert dataset.rems_publish_error is None
    assert dataset.rems_status == REMSStatus.PUBLISHED


@pytest.mark.django_db
def test_admin_dataset_rems_filters(mock_rems):
    """Test DatasetAdmin REMSStatusFilter"""
    not_rems_dataset = factories.PublishedDatasetFactory()
    rems_dataset = factories.REMSDatasetFactory()
    not_published_dataset = factories.REMSDatasetFactory()
    error_dataset = factories.REMSDatasetFactory(rems_publish_error="hups, pieleen meni")

    assert REMSService().publish_dataset(rems_dataset) is not None

    factory = RequestFactory()
    status_dataset = {
        REMSStatus.NOT_REMS: not_rems_dataset,
        REMSStatus.PUBLISHED: rems_dataset,
        REMSStatus.NOT_PUBLISHED: not_published_dataset,
        REMSStatus.ERROR: error_dataset,
    }
    for status, dataset in status_dataset.items():
        request = factory.get(f"/v3/admin/core/dataset?rems_status={status}")
        filter_ = REMSStatusFilter(request, request.GET.dict(), Dataset, DatasetAdmin)
        assert list(filter_.queryset(request, Dataset.objects.all())) == [dataset]
