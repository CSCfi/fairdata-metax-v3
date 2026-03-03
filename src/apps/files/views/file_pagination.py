import logging

from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework.pagination import BasePagination, CursorPagination

from apps.common.pagination import OffsetPagination, TogglablePaginationMixin

logger = logging.getLogger(__name__)


class FileCursorPagination(TogglablePaginationMixin, CursorPagination):
    """Cursor pagination for files."""

    ordering = ["record_created"]  # QuerySet needs to include record_created
    template = None

    page_size = 20  # default
    page_size_query_param = "limit"

    # Set maximum allowed offset. DRF cursor pagination includes an offset in case
    # there are duplicate values for the ordering field.
    offset_cutoff = 100000

    # Declare which query parameters are used by pagination so they can be used in validation
    params = {
        CursorPagination.cursor_query_param,
        page_size_query_param,
        *TogglablePaginationMixin.params,
    }

    def get_ordering(self, request, queryset, view):
        ordering: tuple = super().get_ordering(request, queryset, view)
        # Limit supported ordering values.
        if ordering not in {("record_created",), ("-record_created",)}:
            raise exceptions.ValidationError(
                {
                    "ordering": "Value not allowed for cursor pagination. "
                    + "Allowed values are 'record_created' and '-record_created'."
                }
            )
        return ordering


class FileOffsetOrCursorPagination(BasePagination):
    """File paginator that uses offset or cursor pagination based on request.

    Unlike normal DRF paginators, needs to be initialized with a request
    to determine which child paginator will be used.
    """

    params = {*FileCursorPagination.params, *OffsetPagination.params, "pagination_type"}
    pagination_type: None | str = None
    pagination_type_param = "pagination_type"
    pagination_type_description = """Pagination type.
            Cursor pagination only supports `ordering` values `record_created` and `-record_created`
            and does return total file count, but is more efficient for iterating through
            all files of a project in a storage."""

    def __init__(self, request=None) -> BasePagination:
        if request is None:
            raise ValueError(
                f"{self.__class__.__name__}() needs to be called with a request as argument."
            )
        pagination_type = request.query_params.get(self.pagination_type_param, "offset")

        paginator: BasePagination
        allowed_params: set
        if pagination_type == "offset":
            paginator = OffsetPagination()
            allowed_params = {*OffsetPagination.params, self.pagination_type_param}
        elif pagination_type == "cursor":
            paginator = FileCursorPagination()
            allowed_params = {*FileCursorPagination.params, self.pagination_type_param}
        else:
            raise serializers.ValidationError(
                {
                    self.pagination_type_param: (
                        "Unsupported pagination type. Allowed values are 'offset' and 'cursor'."
                    )
                }
            )

        used_params = self.params.intersection(request.query_params)
        if unallowed := used_params - allowed_params:
            raise serializers.ValidationError(
                dict.fromkeys(
                    sorted(unallowed), f"Not allowed for pagination_type={pagination_type}"
                )
            )

        self._paginator = paginator
        self.pagination_type = pagination_type

    def paginate_queryset(self, queryset, request, view=None):
        return self._paginator.paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return self._paginator.get_paginated_response(data)

    def to_html(self):
        return self._paginator.to_html()

    def pagination_enabled(self, request):
        return self._paginator.pagination_enabled(request)

    def get_schema_operation_parameters(self, view):
        offset_params = OffsetPagination().get_schema_operation_parameters(view)
        cursor_params = FileCursorPagination().get_schema_operation_parameters(view)
        offset_names = {param["name"] for param in offset_params}
        cursor_names = {param["name"] for param in cursor_params}

        added = set()
        params = [
            {
                "name": self.pagination_type_param,
                "required": False,
                "in": "query",
                "description": force_str(self.pagination_type_description),
                "schema": {"type": "string", "enum": ["offset", "cursor"], "default": "offset"},
            }
        ]
        for param in [*offset_params, *cursor_params]:
            name = param["name"]
            if name in added:
                continue
            if name not in cursor_names:
                param["description"] += " Only for offset pagination."
            if name not in offset_names:
                param["description"] += " Only for cursor pagination."
            params.append(param)
            added.add(name)
        return params
