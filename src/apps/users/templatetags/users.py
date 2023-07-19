from django import template
from django.template.defaulttags import CsrfTokenNode
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from users.authentication import SSOAuthentication

register = template.Library()


@register.simple_tag()
def sso_login(request):
    if not SSOAuthentication().is_sso_enabled():
        return ""

    login_url = reverse("login")
    snippet = """
    <li>
        <a href="{href}?next={next}">Login</a>
    </li>
    """
    snippet = format_html(snippet, href=login_url, next=escape(request.path))
    return mark_safe(snippet)


@register.simple_tag(takes_context=True)
def user_menu(context, user):
    logout_url = reverse("logout")
    tokens_url = reverse("tokens")

    # Note: <button> is used here instead of <a> to allow using POST method,
    # and the button is styled in the api.html template look like a link.
    snippet = """
    <li class="dropdown">
        <a href="#" class="dropdown-toggle" data-toggle="dropdown">
            {user}
            <b class="caret"></b>
        </a>
        <ul class="dropdown-menu">
            <li><a href="{tokens_url}">API tokens</a></li>
            <li>
                <form action="{logout_url}" method="post">
                    {csrf}
                    <button class="link" type="submit">Logout</button>
                </form>
            </li>
        </ul>
    </li>
    """
    snippet = format_html(
        snippet,
        user=escape(user),
        tokens_url=tokens_url,
        logout_url=logout_url,
        csrf=CsrfTokenNode().render(context),
    )
    return mark_safe(snippet)
