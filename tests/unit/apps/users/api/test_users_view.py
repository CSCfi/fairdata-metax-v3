import json
import os
import sys
import unittest
from importlib import reload

import pytest
from django.contrib.auth import get_user_model
from django.db.models import signals
from django.urls import clear_url_caches

from apps.core import factories
from apps.core.models import Dataset, FileSet

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def reload_router_urls(settings):
    """Reload router urls.

    Call the returned function to apply settings that affect router urls.
    Automatically reloads urls in teardown step after reverting setting overrides.
    """

    def reload_urlconf(urlconf):
        if urlconf in sys.modules:
            reload(sys.modules[urlconf])

    def func():
        clear_url_caches()
        # root urlconf also needs to be reloaded to propagate changes
        reload_urlconf("apps.router.urls")
        reload_urlconf(settings.ROOT_URLCONF)

    yield func

    # revert changes to settings and reload urls again
    settings.finalize()
    func()


@pytest.fixture
def users_view_enabled(reload_router_urls, settings):
    settings.ENABLE_USERS_VIEW = True
    reload_router_urls()


@pytest.fixture
def users_view_disabled(reload_router_urls, settings):
    settings.ENABLE_USERS_VIEW = False
    reload_router_urls()


def test_users_view_disabled(users_view_disabled, client):
    resp = client.get("/v3/users")
    assert resp.status_code == 404


def test_users_view_enabled(users_view_enabled, client):
    resp = client.get("/v3/users")
    assert resp.status_code == 200


def test_users_view(users_view_enabled, client):
    get_user_model().objects.create(username="test1")
    get_user_model().objects.create(username="test2")
    resp = client.get("/v3/users")
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 2


def test_users_view_delete(users_view_enabled, client):
    get_user_model().objects.create(username="test1")
    resp = client.get("/v3/users/test1")
    assert resp.status_code == 200
    resp = client.delete("/v3/users/test1")
    assert resp.status_code == 204
    resp = client.get("/v3/users/test1")
    assert resp.status_code == 404


def test_users_view_delete_cascade(users_view_enabled, client, dataset_with_files):
    username = dataset_with_files.metadata_owner.user.username
    dataset_id = dataset_with_files.id
    file_set_id = dataset_with_files.file_set.id

    # Deleting user should also remove user datasets and related filesets. Only used in test environments.
    resp = client.delete(f"/v3/users/{username}")
    assert resp.status_code == 204
    resp = client.get(f"/v3/datasets/{dataset_id}")
    assert resp.status_code == 404
    assert FileSet.all_objects.filter(id=file_set_id).count() == 0


def test_users_view_delete_cascade_signals(users_view_enabled, client, dataset_with_files):
    username = dataset_with_files.metadata_owner.user.username
    dataset_handler = unittest.mock.MagicMock()
    fileset_handler = unittest.mock.MagicMock()
    signals.pre_delete.connect(dataset_handler, sender=Dataset)
    signals.pre_delete.connect(fileset_handler, sender=FileSet)

    # Check that deletion signal handlers are called
    resp = client.delete(f"/v3/users/{username}")
    assert resp.status_code == 204
    dataset_handler.assert_called_once()
    fileset_handler.assert_called_once()
