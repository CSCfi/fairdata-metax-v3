import logging

from rest_framework.generics import get_object_or_404
from rest_framework import serializers

from apps.common.views import CommonModelViewSet
from apps.files.models.file import File, FileCharacteristics
from apps.files.permissions import FileCharacteristicsAccessPolicy, FilesAccessPolicy
from apps.files.serializers.file_bulk_serializer import BulkAction
from apps.files.serializers.file_serializer import FileCharacteristicsSerializer
from apps.files.signals import sync_files

logger = logging.getLogger(__name__)


class FileCharacteristicsQueryParamsSerializer(serializers.Serializer):
    dataset = serializers.UUIDField(
        default=None,
        help_text="Use to access characteristics as a member of a dataset the file belongs to.",
    )


class FileCharacteristicsViewSet(CommonModelViewSet):
    http_method_names = ["get", "put", "patch", "delete", "options"]
    access_policy = FileCharacteristicsAccessPolicy
    serializer_class = FileCharacteristicsSerializer
    query_serializers = [{"class": FileCharacteristicsQueryParamsSerializer}]

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", None
        ):  # kwargs are not available in swagger inspection
            return FileCharacteristics.objects.none()

        file = self.get_file_instance()
        return FileCharacteristics.objects.filter(file=file)

    def sync(self, file: File):
        sync_files.send(
            sender=File,
            actions=[{"action": BulkAction.UPDATE, "object": file}],
        )

    def perform_create(self, serializer):
        file = self.get_file_instance()
        characteristics = serializer.save()
        File.objects.filter(id=file.id).update(characteristics=characteristics)
        self.sync(file)

    def update(self, request, *args, **kwargs):
        if not kwargs.get("patch"):
            # Allow creating new object when in PUT mode
            if not self.get_queryset().exists():
                return self.create(request, *args, **kwargs)

        resp = super().update(request, *args, **kwargs)
        self.sync(self.get_file_instance())
        return resp

    def destroy(self, request, *args, **kwargs):
        resp = super().destroy(request, *args, **kwargs)
        self.sync(self.get_file_instance())
        return resp

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "swagger_fake_view", None):
            # kwargs are not available in swagger inspection
            return context
        context["file"] = self.get_file_instance()
        return context

    def get_file_instance(self) -> File:
        if instance := getattr(self, "_file_instance", None):
            return instance
        queryset = File.available_objects.filter(id=self.kwargs["pk"])
        queryset = FilesAccessPolicy().scope_queryset(
            self.request, queryset, dataset_id=self.query_params["dataset"]
        )
        self._file_instance = get_object_or_404(queryset)
        return self._file_instance

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj
