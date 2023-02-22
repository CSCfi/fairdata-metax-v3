import logging

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import exceptions, viewsets

from apps.core.models.catalog_record import Dataset
from apps.core.serializers import DatasetSerializer
from apps.files.models import StorageProject
from apps.files.serializers import DirectorySerializer
from apps.files.views.directory_view import DirectoryCommonQueryParams, DirectoryViewSet
from apps.files.views.file_view import FileCommonFilterset, FileViewSet

logger = logging.getLogger(__name__)


class DatasetFilter(filters.FilterSet):
    title = filters.CharFilter(
        field_name="title__values",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )

    ordering = filters.OrderingFilter(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
        )
    )


class DatasetViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetSerializer
    queryset = Dataset.objects.all()
    filterset_class = DatasetFilter
    http_method_names = ["get", "post", "put", "delete"]


class DatasetDirectoryViewSet(DirectoryViewSet):
    """API for browsing directories of a dataset."""

    def get_params(self):
        """Parse view query parameters."""
        params_serializer = DirectoryCommonQueryParams(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        # dataset id comes from route, storage project is determined from dataset
        dataset_id = self.kwargs["dataset_id"]
        params["dataset"] = dataset_id
        params["exclude_dataset"] = False
        try:
            dataset_files = Dataset.objects.get(id=dataset_id).files
            first_file = dataset_files.first()
            if not first_file:
                raise exceptions.NotFound()
            params["storage_project_id"] = dataset_files.first().storage_project_id
        except (Dataset.DoesNotExist, StorageProject.DoesNotExist):
            raise exceptions.NotFound()
        return params

    @swagger_auto_schema(
        query_serializer=DirectoryCommonQueryParams,
        responses={200: DirectorySerializer},
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)


class DatasetFilesViewSet(FileViewSet):
    filterset_class = FileCommonFilterset
    http_method_names = ["get"]

    def get_queryset(self):
        files = super().get_queryset()
        dataset_id = self.kwargs["dataset_id"]
        return files.filter(datasets=dataset_id)

    # TODO: Support adding files to dataset
    # TODO: Support adding dataset-specific metadata to files
