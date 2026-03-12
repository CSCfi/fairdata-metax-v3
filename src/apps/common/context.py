from contextvars import ContextVar

# Thread and async safe variable for storing the current request.
ctx_request = ContextVar("request", default=None)


class RequestContextMiddleware:
    """Store request in ctx_request context variable.

    Useful when the request is not otherwise available, e.g. logging.

    Use ctx_request.get() to get the request object. Note that
    the stored request is the Django request object and does not
    contain DRF-specific attributes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # In Python 3.14 the token is also a context manager and this can be replaced with:
        #
        # with ctx_request.set(request):
        #   return self.get_response(request)
        token = ctx_request.set(request)
        response = self.get_response(request)
        ctx_request.reset(token)  # restore ctx_request to previous state
        return response
