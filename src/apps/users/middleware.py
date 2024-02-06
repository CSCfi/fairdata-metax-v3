from django.conf import settings


class SameOriginCookiesMiddleware:
    """Allow only specific cookies in CORS requests.

    Cross-origin requests should ignore Django session
    cookies to prevent using logged in Django
    session when SSO cookie is not present.

    Has to be placed before SessionMiddleware to work properly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Remove cookies not in allowed_cookies from request.

        E.g. Etsin cross-origin requests have an `Origin` header
        and `Sec-Fetch-Site: "same-site"`.
        """
        allowed_cookies = {settings.SSO_SESSION_COOKIE, settings.CSRF_COOKIE_NAME}
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        if origin and fetch_site not in {"none", "same-origin"}:
            if fetch_site not in {"none", "same-origin"}:
                request.COOKIES = {
                    key: value for key, value in request.COOKIES.items() if key in allowed_cookies
                }
        return self.get_response(request)
