from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema

from apps.core.serializers import PreservationModelSerializer
from apps.core.views.nested_views import DatasetNestedOneToOneView


@method_decorator(
    name="retrieve", decorator=swagger_auto_schema(operation_description="View Preservation")
)
class PreservationViewSet(DatasetNestedOneToOneView):
    serializer_class = PreservationModelSerializer
    dataset_field_name = "preservation"
    use_defaults_when_object_does_not_exist = True
