import pytest
from django.test import override_settings
from django_q.conf import Conf

from apps.common.tasks import run_task


@pytest.fixture
def enable_tasks(monkeypatch):
    """Enable background tasks"""
    override_settings(
        ENABLE_BACKGROUND_TASKS=True,
    )
    # Enable sync so tasks run immediately instead of delegating it to workers.
    # Because django-q does not respect overridden settings,
    # we need to monkeypatch the Conf.
    monkeypatch.setattr(Conf, "SYNC", True)


def hello(name):
    return f"Hello {name}"


@override_settings(
    ENABLE_BACKGROUND_TASKS=True,
)
def test_tasks(admin_client, enable_tasks):
    run_task(hello, name="World")
    res = admin_client.get("/v3/tasks", content_type="application/json")
    assert res.status_code == 200
    data = res.json()
    assert len(data["results"]) == 1
    task = data["results"][0]
    assert task["kwargs"] == "{'name': 'World'}"
    assert task["result"] == "Hello World"
    assert task["success"] == True


def test_tasks_nonadmin(ida_client):
    res = ida_client.get("/v3/tasks", content_type="application/json")
    assert res.status_code == 403
