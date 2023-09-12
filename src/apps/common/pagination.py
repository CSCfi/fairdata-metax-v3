import coreapi
import coreschema
from django.forms.fields import NullBooleanField
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.pagination import LimitOffsetPagination


class OffsetPagination(LimitOffsetPagination):
    default_limit = 100

    # Allow disabling pagination with pagination=false
    pagination_param = "pagination"
    pagination_description = _("Set false to disable pagination.")

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
