from django.http.response import HttpResponseRedirect


class HttpResponseSeeOther(HttpResponseRedirect):
    """Redirect that also changes method to GET."""

    status_code = 303
