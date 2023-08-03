# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
from drf_yasg.inspectors import NotHandled, ReferencingSerializerInspector

from .fields import URLReferencedModelField


class URLReferencedModelFieldInspector(ReferencingSerializerInspector):
    """Generate swagger for URLReferencedModelField from its child serializer."""

    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        if isinstance(field, URLReferencedModelField):
            return super().field_to_swagger_object(
                field.child, swagger_object_type, use_references, **kwargs
            )
        return NotHandled
