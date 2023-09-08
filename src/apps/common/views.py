from django.shortcuts import render
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

# Create your views here.


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class PatchModelMixin:
    """ViewSet mixin for patching stuff"""

    def update(self, request, *args, **kwargs):
        """Like UpdateModelMixin.update but with support for 'patch' kwarg."""
        patch = kwargs.pop("patch", False)
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, patch=patch)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["patch"] = True
        return self.update(request, *args, **kwargs)
