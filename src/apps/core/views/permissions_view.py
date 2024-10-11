from rest_framework.generics import get_object_or_404

from apps.core.models.catalog_record.dataset_permissions import DatasetPermissions
from apps.core.permissions import DatasetPermissionsAccessPolicy
from apps.core.serializers import (
    DatasetPermissionsSerializer,
    DatasetPermissionsUserModelSerializer,
)
from apps.core.views.nested_views import DatasetNestedViewSet


class DatasetPermissionsViewSet(DatasetNestedViewSet):
    """Dataset permissions."""

    http_method_names = ["get", "options"]
    serializer_class = DatasetPermissionsSerializer
    access_policy = DatasetPermissionsAccessPolicy

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return self.serializer_class.Meta.model.available_objects.none()

        dataset = self.get_dataset_instance()
        return self.serializer_class.Meta.model.all_objects.filter(datasets=dataset)

    def get_object(self):
        queryset = self.get_queryset()
        permissions: DatasetPermissions = get_object_or_404(queryset)
        self.check_object_permissions(self.request, permissions)
        dataset = self.get_dataset_instance()
        permissions.set_context_dataset(dataset)
        return permissions


class DatasetPermissionsEditorsViewSet(DatasetNestedViewSet):
    """List of dataset editors."""

    http_method_names = ["get", "post", "delete", "options"]
    serializer_class = DatasetPermissionsUserModelSerializer
    lookup_field = "username"
    access_policy = DatasetPermissionsAccessPolicy

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return self.serializer_class.Meta.model.available_objects.none()

        dataset = self.get_dataset_instance()
        return self.serializer_class.Meta.model.all_objects.filter(
            dataset_edit_permissions__datasets=dataset
        )

    def perform_create(self, serializer):
        dataset = self.get_dataset_instance()
        serializer.save(dataset=dataset)
        dataset.permissions.create_snapshot()

    def perform_destroy(self, instance):
        dataset = self.get_dataset_instance()
        dataset.permissions.editors.remove(instance)
        dataset.permissions.create_snapshot()