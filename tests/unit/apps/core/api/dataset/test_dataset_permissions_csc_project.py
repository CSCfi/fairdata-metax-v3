import logging

import pytest

from apps.core.factories import DatasetFactory, FileSetFactory, PublishedDatasetFactory

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def test_dataset_permissions_csc_project_list(user_client):
    """Test that draft dataset is listed for csc_project member."""
    dataset = DatasetFactory()  # draft dataset
    fileset = FileSetFactory(dataset=dataset)
    res = user_client.get("/v3/datasets")
    assert res.status_code == 200
    assert res.data["count"] == 0

    user_client._user.csc_projects = [fileset.storage.csc_project]
    user_client._user.save()

    res = user_client.get("/v3/datasets")
    assert res.status_code == 200
    assert res.data["count"] == 1


def test_dataset_permissions_csc_project_list_owned_or_shared(user_client):
    """Test that only_owned_or_shared includes datasets from user's csc_project."""
    dataset = PublishedDatasetFactory()
    fileset = FileSetFactory(dataset=dataset)

    res = user_client.get("/v3/datasets?only_owned_or_shared=true")
    assert res.status_code == 200
    assert res.data["count"] == 0

    user_client._user.csc_projects = [fileset.storage.csc_project]
    user_client._user.save()

    res = user_client.get("/v3/datasets?only_owned_or_shared=true")
    assert res.status_code == 200
    assert res.data["count"] == 1


def test_dataset_permissions_csc_project_detail(user_client):
    """Test that user can access and modify dataset in csc_project."""
    dataset = DatasetFactory()  # draft dataset
    fileset = FileSetFactory(dataset=dataset)

    res = user_client.get(f"/v3/datasets/{dataset.id}")
    assert res.status_code == 404

    user_client._user.csc_projects = [fileset.storage.csc_project]
    user_client._user.save()

    res = user_client.get("/v3/datasets")
    assert res.status_code == 200

    res = user_client.patch(
        f"/v3/datasets/{dataset.id}",
        {"title": {"en": "hello world"}},
        content_type="application/json",
    )
    assert res.status_code == 200
    assert res.data["title"] == {"en": "hello world"}
