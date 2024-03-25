import logging

from django.db.models import Q

from apps.common.permissions import BaseAccessPolicy

logger = logging.getLogger(__name__)


class DatasetAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": [
                "update",
                "destroy",
                "partial_update",
                "new_version",
                "create_draft",
                "publish",
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_edit_allowed",
        },
        {
            "action": "convert_from_legacy",
            "principal": "*",
            "effect": "allow",
        },
        {
            # Note that there is no actual "download" action in the viewset at the moment.
            "action": ["<op:download>"],
            "principal": "*",
            "effect": "allow",
            "condition": "is_download_allowed",
        },
        {
            "action": ["<op:custom_metadata_owner>"],
            "principal": "group:service",
            "effect": "allow",
        },
        {
            "action": ["<op:flush>"],  # hard delete dataset
            "principal": "group:service",
            "effect": "allow",
            "condition": "is_edit_allowed",
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",  # Catalog permission checked in viewset perform_create
        },
    ] + BaseAccessPolicy.statements

    def is_edit_allowed(self, request, view, action) -> bool:
        dataset = view.get_object()
        return dataset.has_permission_to_edit(request.user)

    def is_metadata_owner(self, request, view, action) -> bool:
        dataset = view.get_object()
        logger.info(request.user)
        if dataset.metadata_owner:
            return request.user == dataset.metadata_owner.user
        else:
            return False

    def is_download_allowed(self, request, view, action) -> bool:
        dataset = view.get_object()
        if access_rights := dataset.access_rights:
            return access_rights.is_data_available(request, dataset)
        return False

    @classmethod
    def scope_queryset(cls, request, queryset):
        from .models import Dataset

        if q := super().scope_queryset(request, queryset):
            return q
        elif request.user.is_anonymous:
            return queryset.filter(state=Dataset.StateChoices.PUBLISHED)
        groups = request.user.groups.all()
        return queryset.filter(
            Q(state=Dataset.StateChoices.PUBLISHED)
            | Q(metadata_owner__user=request.user)
            | Q(system_creator=request.user)
            | Q(published_revision__gt=0)
            | Q(data_catalog__dataset_groups_admin__in=groups)
        )

    @classmethod
    def scope_queryset_owned_or_shared(cls, request, queryset):
        from .models import Dataset

        if request.user.is_anonymous:
            return Dataset.available_objects.none()
        return queryset.filter(metadata_owner__user=request.user)


class DataCatalogAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["create"],
            "principal": "group:service",
            "effect": "allow",
        },
        {
            "action": ["update", "partial_update", "destroy"],
            "principal": "group:service",
            "effect": "allow",
            "condition": "is_system_creator",
        },
        {
            "action": ["<op:create_dataset>"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_creating_datasets_allowed",
        },
        {
            "action": ["<op:admin_dataset>"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_dataset_admin",
        },
    ] + BaseAccessPolicy.statements

    def is_creating_datasets_allowed(self, request, view, action) -> bool:
        """Return True if user is allowed to create datasets in this catalog."""
        user = request.user
        if user.is_superuser:
            return True

        catalog = view.get_object()
        user_groups = user.groups.all()
        return catalog.dataset_groups_create.intersection(user_groups).exists()

    def is_dataset_admin(self, request, view, action) -> bool:
        """Return True if user is allowed to edit all datasets in this catalog."""
        user = request.user
        if user.is_superuser:
            return True

        catalog = view.get_object()
        user_groups = user.groups.all()
        return catalog.dataset_groups_admin.intersection(user_groups).exists()


class LegacyDatasetAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["create", "update", "partial_update", "destroy"],
            "principal": "group:v2_migration",
            "effect": "allow",
        },
    ] + BaseAccessPolicy.statements


class DatasetNestedAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["create", "update", "partial_update", "destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_dataset_owner",
        },
    ] + BaseAccessPolicy.statements

    def is_dataset_owner(self, request, view, action) -> bool:
        dataset = view.get_dataset_instance()
        if not dataset.metadata_owner:
            return request.user == dataset.system_creator
        else:
            return (
                request.user == dataset.metadata_owner.user
                or request.user == dataset.system_creator
            )


class ContractAccessPolicy(BaseAccessPolicy):
    pass
