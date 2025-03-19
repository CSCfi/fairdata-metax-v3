from http.cookies import SimpleCookie

from django.test import RequestFactory
import pytest

from apps.users.middleware import SameOriginCookiesMiddleware

@pytest.mark.django_db
def test_same_origin_cookies_middleware(user, client, settings):
    settings.SSO_SESSION_COOKIE = "sso_cookie"
    settings.CSRF_COOKIE_NAME = "csrf_cookie"
    client.force_login(user)

    cookies = {}

    def set_cookies(request):
        cookies.clear()
        cookies.update(request.COOKIES)

    request = RequestFactory()
    sso_cookies = {
        "sso_cookie": "something",
        "csrf_cookie": "something else",
    }
    all_cookies = {
        "unrelated_cookie": "somevalue",
        **sso_cookies,
    }
    request.cookies = SimpleCookie(all_cookies)
    middleware = SameOriginCookiesMiddleware(get_response=set_cookies)

    # Ordinary request should get all cookies
    middleware(request.get("/"))
    assert cookies == all_cookies

    # Cross-origin request should get only SSO-related cookies
    middleware(
        request.get("/", HTTP_ORIGIN="https://example.com", HTTP_SEC_FETCH_SITE="same-site")
    )
    assert cookies == sso_cookies
