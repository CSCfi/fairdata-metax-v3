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
from drf_yasg.utils import force_serializer_instance, param_list_to_odict

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
