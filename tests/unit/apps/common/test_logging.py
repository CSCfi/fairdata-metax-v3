import logging

import pytest
from django.http import HttpResponse
from django.test import override_settings
from django.urls import re_path

logger = logging.getLogger("test")


# Setup a fake view that logs all requests
def fake_view(request):
    logger.info(f"Requested {request.path}")
    return HttpResponse("hello world")


urlpatterns = [
    re_path(".*", fake_view),
]


@pytest.mark.django_db()
@override_settings(
    ROOT_URLCONF="tests.unit.apps.common.test_logging",
    MIDDLEWARE=[
        "apps.common.context.RequestContextMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    ],
)
def test_log_source(
    caplog,
    admin_client,
    appsupport_client,
    user_client,
):
    """Test that log records include the request source attribute."""
    logging.disable(logging.NOTSET)
    admin_client.get("/something")
    appsupport_client.get("/something")
    user_client.get("/something")
    user_client.get("/something", headers={"origin": "https://qvain.fairdata.fi"})

    sources = [record.source for record in caplog.records]
    assert sources == ["admin", "appsupport_user", "-", "qvain.fairdata.fi"]
