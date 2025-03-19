from datetime import timedelta
from typing import Optional, Tuple

import jwt
import pytest
from dateutil.parser import parse
from django.conf import settings as django_settings
from rest_framework import exceptions
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory

from apps.users.authentication import SSOAuthentication
from apps.users.models import MetaxUser

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def make_sso_auth_request(enable_sso):
    def f(sso_session, use_wrong_key=False) -> Tuple[Optional[MetaxUser], Optional[str]]:
        factory = APIRequestFactory()
        request = factory.get("/")
        if sso_session:
            key = "this_key_is_wrong" if use_wrong_key else django_settings.SSO_SECRET_KEY
            sso_token = jwt.encode(sso_session, key=key)
            request.COOKIES[django_settings.SSO_SESSION_COOKIE] = sso_token
        try:
            authentication = SSOAuthentication()
            auths = authentication.authenticate(request=request)
            if auths is None:
                return None, None
            return auths[0], None
        except exceptions.AuthenticationFailed as e:
            return None, e.get_codes()

    return f


# Successful authentication tests


def test_sso_authentication_ok(make_sso_auth_request, sso_session_teppo):
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user.username == "fd_teppo3"
    assert user.csc_projects == ["fd_teppo3_project"]
    assert error == None


def test_sso_authentication_sync(make_sso_auth_request, sso_session_teppo, sso_format_datetime):
    user, error = make_sso_auth_request(sso_session_teppo)
    sso_session_teppo["services"]["IDA"]["projects"] = ["fd_teppo3_project", "new_project"]
    sso_session_teppo["initiated"] = sso_format_datetime(
        parse(sso_session_teppo["initiated"]) + timedelta(hours=1)
    )

    # session is newer than previous sync, should sync user details
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user.csc_projects == ["fd_teppo3_project", "new_project"]
    assert error == None


def test_sso_authentication_dont_sync_old(make_sso_auth_request, sso_session_teppo):
    make_sso_auth_request(sso_session_teppo)
    sso_session_teppo["services"]["IDA"]["projects"] = ["fd_teppo3_project", "new_project"]

    # session is not newer than previous sync, should not sync user details
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user.csc_projects == ["fd_teppo3_project"]
    assert error == None


def test_sso_authentication_unauthenticated(make_sso_auth_request):
    user, error = make_sso_auth_request(None)
    assert user == None
    assert error == None


# Configuration tests


def test_sso_authentication_disabled(make_sso_auth_request, sso_session_teppo, settings):
    settings.ENABLE_SSO_AUTH = False
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user == None
    assert error == None


def test_sso_authentication_missing_secret(make_sso_auth_request, sso_session_teppo, settings):
    settings.SSO_SECRET_KEY = ""
    user, error = make_sso_auth_request(sso_session_teppo)
    assert error == "invalid_sso_configuration"


def test_sso_authentication_missing_cookie_setting(
    make_sso_auth_request, sso_session_teppo, settings
):
    settings.SSO_SESSION_COOKIE = ""
    user, error = make_sso_auth_request(sso_session_teppo)
    assert error == "invalid_sso_configuration"


def test_sso_authentication_wrong_secret(make_sso_auth_request, sso_session_teppo):
    user, error = make_sso_auth_request(sso_session_teppo, use_wrong_key=True)
    assert error == "authentication_failed"


# User error tests


def test_sso_authentication_missing_fairdata_user_id(make_sso_auth_request, sso_session_teppo):
    sso_session_teppo["fairdata_user"]["id"] = None
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user == None
    assert error == "missing_fairdata_user_id"


def test_sso_authentication_missing_organization_user_id(make_sso_auth_request, sso_session_teppo):
    sso_session_teppo["authenticated_user"]["organization"]["id"] = None
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user == None
    assert error == "missing_organization_id"


def test_sso_authentication_locked_user(make_sso_auth_request, sso_session_teppo):
    sso_session_teppo["fairdata_user"]["locked"] = True
    user, error = make_sso_auth_request(sso_session_teppo)
    assert user == None
    assert error == "fairdata_user_locked"
