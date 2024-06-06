from collections import OrderedDict

import coreapi
import coreschema
from django.forms.fields import NullBooleanField
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class OffsetPagination(LimitOffsetPagination):
    default_limit = 20

    # Allow disabling pagination with pagination=false
    pagination_param = "pagination"
    pagination_description = _("Set false to disable pagination.")

    # Declare which query parameters are used by pagination so they can be used in validation
    params = {
        LimitOffsetPagination.limit_query_param,
        LimitOffsetPagination.offset_query_param,
        pagination_param,
    }

    def pagination_enabled(self, request):
        try:
            value = request.query_params[self.pagination_param]
            if NullBooleanField().to_python(value) == False:
                return False
        except (KeyError, ValueError):
            pass
        return True

    def paginate_queryset(self, queryset, request, view=None):
        if not self.pagination_enabled(request):
            return None
        return super().paginate_queryset(queryset, request, view)

    def aggregate_queryset(self, queryset):
        raise NotImplementedError('"aggregate_queryset()" must be implemented.')

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )

    def get_schema_fields(self, view):
        fields = super().get_schema_fields(view)
        fields.append(
            coreapi.Field(
                name=self.pagination_param,
                required=False,
                location="query",
                schema=coreschema.Boolean(
                    title="Pagination",
                    description=force_str(self.pagination_description),
                    default=True,
                ),
            ),
        )
        return fields

    def get_schema_operation_parameters(self, view):
        parameters = super().get_schema_operation_parameters(view)
        parameters.append(
            {
                "name": self.pagination_param,
                "required": False,
                "in": "query",
                "description": force_str(self.pagination_description),
                "schema": {"type": "boolean"},
            }
        )
        return parameters


class DefaultOffsetPagination(OffsetPagination):
    def aggregate_queryset(self, queryset):
        return None
