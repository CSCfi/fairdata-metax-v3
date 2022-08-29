from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

class ReferenceDataPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


def get_viewset_for_model(model):
    class ReferenceDataViewSet(viewsets.ReadOnlyModelViewSet):
        """Generic viewset for reference data objects."""

        serializer_class = model.get_serializer()
        queryset = model.available_objects.filter(
            is_reference_data=True
        ).prefetch_related("broader", "narrower")
        pagination_class = ReferenceDataPagination

    return ReferenceDataViewSet
