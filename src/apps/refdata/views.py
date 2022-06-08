from rest_framework import viewsets, filters


class ReferenceDataViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.SearchFilter]
    search_fields = ("pref_label__values",)
