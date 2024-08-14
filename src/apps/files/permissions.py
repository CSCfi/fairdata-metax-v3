from django.conf import settings

from apps.common.permissions import BaseAccessPolicy


class BaseFilesAccessPolicy(BaseAccessPolicy):
    statements = [
        {"action": "*", "principal": ["admin", "group:ida"], "effect": "allow"},
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
