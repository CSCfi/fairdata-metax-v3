from rest_framework.test import APIRequestFactory

from apps.users.models import MetaxUser
from apps.users.templatetags.users import sso_login, user_menu


def test_sso_login_tag(enable_sso):
    factory = APIRequestFactory()
    request = factory.get("/somepath")
    rendered = sso_login(request)
    assert '<a href="/auth/login?next=/somepath">Login</a>' in rendered


def test_sso_login_tag_disabled(disable_sso):
    factory = APIRequestFactory()
    request = factory.get("/somepath")
    rendered = sso_login(request)
    assert rendered == ""


def test_user_menu_tag(enable_sso):
    context = {"csrf_token": "token_value"}
    rendered = user_menu(context, MetaxUser(username="moro"))
    assert '<form action="/auth/logout" method="post">' in rendered
    assert '<a href="/auth/tokens">' in rendered
    assert '<input type="hidden" name="csrfmiddlewaretoken" value="token_value">' in rendered
