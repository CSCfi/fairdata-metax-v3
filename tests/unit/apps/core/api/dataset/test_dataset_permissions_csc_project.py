import logging
from urllib.parse import parse_qs

import pytest
from django.conf import settings as django_settings
from tests.utils import matchers

from apps.core.factories import (
    DatasetFactory,
    FileSetFactory,
    FileStorageFactory,
    PublishedDatasetFactory,
)

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.django_db, pytest.mark.dataset]


def project_status_callback(request, context):
    project_id = parse_qs(request.body)["id"][0]
    if project_id != "test_project":
        context.status_code = 404
        return "project not found"
    return {
        "id": "test_project",
        "modified": "2023-04-03T10:45:57Z",
        "scope": "academic",
        "state": "open",
        "title": "Fairdata test project",
        "types": ["ida"],
        "users": {
            "test_user": {
                "email": "teppo@example.com",
                "locked": False,
                "name": "Teppo Testaaja",
            },
            "test_user2": {
                "email": "matti@example.com",
                "locked": False,
                "name": "Matti Mestaaja",
            },
            "test_locked": {
                "email": "locked@example.com",
                "locked": True,
                "name": "Locked User",
            },
        },
    }


@pytest.fixture
def sso_projects(requests_mock, enable_sso):
    return requests_mock.post(
        f"{django_settings.SSO_HOST}/project_status",
        json=project_status_callback,
    )


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


def test_dataset_permissions_sso_projects(admin_client, sso_projects):
    logging.disable(logging.NOTSET)

    dataset = DatasetFactory()  # draft dataset
    FileSetFactory(
        dataset=dataset,
        storage=FileStorageFactory(storage_service="ida", csc_project="test_project"),
    )

    res = admin_client.get(
        f"/v3/datasets/{dataset.id}/permissions", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["csc_project"] == "test_project"
    assert res.data["csc_project_members"] == [
        matchers.DictContaining({"username": "test_user"}),
        matchers.DictContaining({"username": "test_user2"}),
    ]


def test_dataset_permissions_sso_projects_notfound(admin_client, sso_projects):
    logging.disable(logging.NOTSET)

    dataset = DatasetFactory()  # draft dataset
    FileSetFactory(
        dataset=dataset,
        storage=FileStorageFactory(storage_service="ida", csc_project="not_test_project"),
    )

    res = admin_client.get(
        f"/v3/datasets/{dataset.id}/permissions", content_type="application/json"
    )
    assert res.status_code == 200
    assert res.data["csc_project_members"] == []
