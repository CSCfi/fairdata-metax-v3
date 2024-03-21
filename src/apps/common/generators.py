from drf_yasg.generators import OpenAPISchemaGenerator


class SortingOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    """Schema generator that sorts definitions list by key."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        # Sort model definitions
        schema.definitions = {key: schema.definitions[key] for key in sorted(schema.definitions)}

        # Remove the / path from swagger
        schema.paths.pop("/", None)

        return schema
