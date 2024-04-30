from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, _get_error_details
from rest_framework.serializers import ValidationError
from rest_framework.views import exception_handler as default_handler

from apps.common.helpers import get_attr_or_item


class TopLevelValidationError(APIException):
    """Validation error that is raised to top level instead of serializer trying to gather all errors.

    Useful when same error output is desired outside serialization and e.g. in a nested serializer.
    """

    status_code = status.HTTP_400_BAD_REQUEST


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
