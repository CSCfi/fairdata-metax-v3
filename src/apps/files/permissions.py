from django.conf import settings

from apps.common.permissions import BaseAccessPolicy
from apps.files.models.file import File


class BaseFilesAccessPolicy(BaseAccessPolicy):
    statements = [
        {"action": "*", "principal": ["admin", "group:ida", "group:pas"], "effect": "allow"},
    ]

    @classmethod
    def can_view_dataset(cls, request, dataset_id):
        # Allow viewing dataset files if user can view dataset
        from apps.core.models import Dataset
        from apps.core.permissions import DatasetAccessPolicy

        datasets = Dataset.available_objects.all()
        return (
            DatasetAccessPolicy.scope_queryset(request, queryset=datasets)
            .filter(id=dataset_id)
            .exists()
        )


class FilesAccessPolicy(BaseFilesAccessPolicy):
    statements = BaseFilesAccessPolicy.statements + [
        {
            "action": ["list", "retrieve", "<safe_methods>"],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": ["from_legacy", "destroy_list"],
            "principal": "group:v2_migration",
            "effect": "allow",
        },
    ]

    @classmethod
    def scope_queryset(cls, request, queryset, dataset_id=None):
        service_groups = settings.PROJECT_STORAGE_SERVICE_USER_GROUPS
        if (q := super().scope_queryset(request, queryset)) is not None:
            return q
        elif request.user.groups.filter(name__in=service_groups).exists():
            return queryset
        elif dataset_id:
            if cls.can_view_dataset(request, dataset_id):
                return queryset
            else:
                return queryset.none()
        else:
            csc_projects = getattr(request.user, "csc_projects", [])
            return queryset.filter(storage__csc_project__in=csc_projects)


class FileCharacteristicsAccessPolicy(FilesAccessPolicy):
    statements = FilesAccessPolicy.statements + [
        {
            "action": ["*"],
            "principal": "*",
            "condition": "is_project_or_dataset_member",
            "effect": "allow",
        },
    ]

    def is_project_or_dataset_member(self, request, view, action) -> bool:
        service_groups = settings.PROJECT_STORAGE_SERVICE_USER_GROUPS
        if request.user.groups.filter(name__in=service_groups).exists():
            return True

        # Allow editing characteristics if user belongs to csc_project of file
        file: File = view.get_file_instance()
        csc_projects = getattr(request.user, "csc_projects", [])
        if file.storage.csc_project in csc_projects:
            return True

        # Allow editing characteristics if user can edit a dataset the file belongs to
        from apps.core.models.catalog_record.dataset import Dataset
        from apps.core.permissions import DatasetAccessPolicy

        datasets = Dataset.objects.filter(file_set__files=file)
        return DatasetAccessPolicy.scope_queryset_owned_or_shared(
            request, queryset=datasets
        ).exists()


class DirectoriesAccessPolicy(BaseFilesAccessPolicy):
    statements = BaseFilesAccessPolicy.statements + [
        {
            "action": ["list"],
            "principal": ["*"],
            "condition": "can_view_directory",
            "effect": "allow",
        },
    ]

    def can_view_directory(self, request, view, action):
        params = view.query_params
        if dataset_id := params["dataset"]:
            return self.can_view_dataset(request, dataset_id)
        else:
            csc_projects = getattr(request.user, "csc_projects", [])
            return params["csc_project"] in csc_projects
