from posixpath import basename
from rest_framework import viewsets, filters

from apps.refdata.models import FieldOfScience


def get_viewset_for_model(model):
    class ReferenceDataViewSet(viewsets.ReadOnlyModelViewSet):
        """Generic viewset for reference data objects."""

        serializer_class = model.get_serializer()
        queryset = model.available_objects.filter(
            is_reference_data=True
        ).prefetch_related("broader", "narrower")

    return ReferenceDataViewSet
