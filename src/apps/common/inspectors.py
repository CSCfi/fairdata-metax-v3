# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
from typing import List

from drf_yasg import openapi
from drf_yasg.errors import SwaggerGenerationError
from drf_yasg.inspectors import (
    FieldInspector,
    NotHandled,
    ReferencingSerializerInspector,
    SwaggerAutoSchema,
)
from drf_yasg.utils import force_serializer_instance, no_body, param_list_to_odict

from .serializers.fields import URLReferencedModelField


class URLReferencedModelFieldInspector(ReferencingSerializerInspector):
    """Generate swagger for URLReferencedModelField from its child serializer."""

    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        if isinstance(field, URLReferencedModelField):
            return super().field_to_swagger_object(
                field.child, swagger_object_type, use_references, **kwargs
            )
        return NotHandled


class SwaggerDescriptionInspector(FieldInspector):
    """Inspector that reads description from Serializer.Meta.swagger_description."""

    def process_result(self, result, method_name, obj, **kwargs):
        if isinstance(result, openapi.Schema.OR_REF):
            # traverse any references and alter the Schema object in place
            schema = openapi.resolve_ref(result, self.components)
            if meta := getattr(obj, "Meta", None):
                if description := getattr(meta, "swagger_description", None):
                    schema["description"] = description

        return result


class ExtendedSwaggerAutoSchema(SwaggerAutoSchema):
    """Class that generates the swagger documentation for views."""

    def get_tags(self, operation_keys=None):
        """Return tag for operation, used for grouping endpoints in Swagger."""
        operation_keys = operation_keys or self.operation_keys

        tags = self.overrides.get("tags")
        if not tags:
            if operation_keys[0] == "v3":
                # Group e.g. /v3/datasets in "datasets" instead of having everything in "v3"
                tags = [operation_keys[1]]
            else:
                tags = [operation_keys[0]]

        return tags

    def get_request_serializer(self):
        """Return the request serializer (used for parsing the request payload) for this endpoint.

        Extended to not use the default serializer for custom actions.
        """

        from drf_yasg.generators import is_custom_action

        body_override = self._get_request_body_override()

        action = self.operation_keys[-1]
        if (
            body_override is None
            and self.method in self.implicit_body_methods
            and not is_custom_action(action)  # Remove default body schema from custom actions
        ):
            return self.get_view_serializer()

        if body_override is no_body:
            return None

        return body_override

    def get_query_parameters(self) -> List[openapi.Parameter]:
        """Return the query parameters accepted by this view.

        Extended to allow listing query parameter serializers
        in `ViewSet.get_query_serializer_classes` method.
        """
        parameters = super().get_query_parameters()

        getter = getattr(self.view, "get_query_serializer_classes", lambda: [])
        for serializer in getter():
            serializer = force_serializer_instance(serializer)
            serializer_parameters = self.serializer_to_parameters(serializer, in_=openapi.IN_QUERY)

            old_params = set(param_list_to_odict(parameters))
            new_params = set(param_list_to_odict(serializer_parameters))

            if conflicts := old_params & new_params:
                raise SwaggerGenerationError(
                    f"your query serializer {serializer.__class__} contains fields that conflict with the "
                    f"filter_backend or paginator_class or another query serializer "
                    f"on the view - {self.method} {self.path} {conflicts=}"
                )
            parameters += serializer_parameters
        return parameters
