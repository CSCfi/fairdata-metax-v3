import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from apps.common.views import CommonModelViewSet
from apps.core.models import Dataset
from apps.core.permissions import DatasetAccessPolicy, DatasetNestedAccessPolicy

logger = logging.getLogger(__name__)


class DatasetNestedViewSet(CommonModelViewSet):
    access_policy = DatasetNestedAccessPolicy

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return self.serializer_class.Meta.model.available_objects.none()

        dataset = self.get_dataset_instance()
        return self.serializer_class.Meta.model.available_objects.filter(dataset=dataset)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        self.get_dataset_instance().signal_update()
        return resp

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        self.get_dataset_instance().signal_update()
        return resp

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        self.get_dataset_instance().signal_update()
        return resp

    def perform_create(self, serializer):
        self.get_dataset_instance()
        return serializer.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "swagger_fake_view", None):
            # kwargs are not available in swagger inspection
            return context
        context["dataset"] = self.get_dataset_instance()
        return context

    def get_dataset_instance(self) -> Dataset:
        if instance := getattr(self, "_dataset_instance", None):
            return instance
        try:
            dataset_qs = Dataset.available_objects.filter(id=self.kwargs["dataset_pk"])

            # Lock dataset row for the duration of the transaction
            if self.request.method not in ("GET", "OPTIONS"):
                Dataset.lock_for_update(id=self.kwargs["dataset_pk"])
            dataset_qs = DatasetAccessPolicy().scope_queryset(self.request, dataset_qs)
        except DjangoValidationError:  # E.g. invalid UUID
            dataset_qs = Dataset.objects.none()
        self._dataset_instance: Dataset = get_object_or_404(dataset_qs)
        return self._dataset_instance


class DatasetNestedOneToOneView(DatasetNestedViewSet):
    http_method_names = ["get", "put", "patch", "delete", "options"]

    # Enable to make non-write operations return an unsaved object with
    # default values instead of a 404 error when object does not exist.
    # Also allows creating a new object when using PATCH.
    use_defaults_when_object_does_not_exist = False

    def __init__(self, *args, **kwargs):
        if not getattr(self, "dataset_field_name", None):
            raise ValueError(f"Missing dataset_field_name from {self.__class__.__name__}")
        super().__init__(*args, **kwargs)

    def get_object(self):
        queryset = self.get_queryset()
        model = self.serializer_class.Meta.model

        if self.use_defaults_when_object_does_not_exist:
            try:
                obj = queryset.get()
            except model.DoesNotExist:
                if self.request.method in ["GET", "OPTIONS"]:
                    obj = model(id=None)
                else:
                    raise Http404(f"No {model._meta.object_name} matches the given query.")
        else:
            obj = get_object_or_404(queryset)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_save(self, serializer):
        """Create or update an instance and associate it with the dataset."""
        instance = serializer.save()
        dataset = self.get_dataset_instance()
        setattr(dataset, self.dataset_field_name, instance)
        dataset.save()

    def perform_create(self, serializer):
        self.perform_save(serializer)

    def perform_update(self, serializer):
        self.perform_save(serializer)

    def destroy(self, request, *args, **kwargs):
        if self.use_defaults_when_object_does_not_exist and not self.get_queryset().exists():
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if self.use_defaults_when_object_does_not_exist and not self.get_queryset().exists():
            # PATCH works like PUT when object does not exist
            return self.update(request, *args, **kwargs)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not kwargs.get("patch"):
            # Allow creating new object when in PUT mode
            if not self.get_queryset().exists():
                return self.create(request, *args, **kwargs)
        return super().update(request, *args, **kwargs)
