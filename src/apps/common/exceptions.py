from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import exception_handler as default_handler

from apps.common.helpers import get_attr_or_item


def exception_handler(exc, context):
    """Handler for DRF exceptions."""

    # Include error codes for authentication errors to
    # make it easier for other services to determine
    # cause of failure.
    response = default_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None and isinstance(exc, AuthenticationFailed):
        response.data["code"] = get_attr_or_item(exc.detail, "code")

    return response
