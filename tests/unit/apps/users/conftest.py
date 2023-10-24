import logging
from datetime import datetime, timedelta

import jwt
import pytest
from django.conf import settings as django_settings
from rest_framework.test import APIClient

from apps.users.models import MetaxUser


@pytest.fixture
def user_as_json():
    return {"username": "test_user", "password": "teppo"}


@pytest.fixture
def enable_sso(settings):
    settings.ENABLE_SSO_AUTH = True
    settings.SSO_SECRET_KEY = "TOP_SECRET"
    settings.SSO_SESSION_COOKIE = "sso_session_test"
    settings.SSO_HOST = "https://fake-sso"
    settings.SSO_METAX_SERVICE_NAME = "METAX"


@pytest.fixture
def disable_sso(settings):
    settings.ENABLE_SSO_AUTH = False


@pytest.fixture
def sso_format_datetime():
    def f(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return f


@pytest.fixture
def get_sso_token():
    def f(sso_session):
        return jwt.encode(sso_session, key=django_settings.SSO_SECRET_KEY)

    return f


@pytest.fixture
def sso_session_teppo(sso_format_datetime):
    now = datetime.now()
    exp = now + timedelta(days=1)
    return {
        "authenticated_user": {
            "email": "fairdata-test@postit.csc.fi",
            "firstname": "fd_teppo_first",
            "id": "fd_teppo3",
            "identity_provider": "CSCID",
            "lastname": "fd_teppo_läst",
            "organization": {"id": "csc.fi", "name": "CSC - Tieteen tietotekniikan keskus Oy"},
        },
        "exp": exp.timestamp(),
        "expiration": sso_format_datetime(exp),
        "fairdata_user": {"id": "fd_teppo3", "locked": False},
        "id": "2023-05-29-063118c7d228be69bf40be89e9d6c221b3d23e",
        "initiated": sso_format_datetime(now),
        "initiating_service": "METAX",
        "language": "en",
        "projects": {"fd_teppo3_project": {"services": ["ETSIN", "IDA", "QVAIN"]}},
        "redirect_url": "https://qvain.fd-dev.csc.fi",
        "services": {
            "IDA": {"projects": ["fd_teppo3_project"]},
        },
    }
