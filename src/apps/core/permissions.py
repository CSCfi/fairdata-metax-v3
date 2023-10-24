import logging

from django.db.models import Q

from apps.common.permissions import BaseAccessPolicy

logger = logging.getLogger(__name__)


class DatasetAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["update", "destroy", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_metadata_owner",
        },
        {"action": ["create"], "principal": "authenticated", "effect": "allow"},
    ] + BaseAccessPolicy.statements

    def is_metadata_owner(self, request, view, action) -> bool:
        dataset = view.get_object()
        logger.info(request.user)
        if dataset.metadata_owner:
            return request.user == dataset.metadata_owner.user
        else:
            return False

    @classmethod
    def scope_queryset(cls, request, queryset):
        from .models import Dataset

        if q := super().scope_queryset(request, queryset):
            return q
        elif request.user.is_anonymous:
            return Dataset.only_latest_published()

        return queryset.filter(
            Q(state=Dataset.StateChoices.PUBLISHED)
            | Q(metadata_owner__user=request.user)
            | Q(system_creator=request.user)
            | Q(published_revision__gt=0)
        )


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


class MetadataProviderAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["create", "update", "partial_update", "destroy"],
            "principal": "group:service",
            "effect": "allow",
        },
        {
            "action": ["update", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_system_creator",
        },
    ] + BaseAccessPolicy.statements

    @classmethod
    def scope_queryset(cls, request, queryset):
        if request.user.is_anonymous:
            return queryset.none()
        return queryset
