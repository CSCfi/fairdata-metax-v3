import logging

from rest_access_policy import AccessPolicy

logger = logging.getLogger(__name__)


class BaseAccessPolicy(AccessPolicy):
    id = "base-policy"
    statements = [
        {"action": ["list", "retrieve", "<safe_methods>"], "principal": "*", "effect": "allow"},
        {"action": "*", "principal": "admin", "effect": "allow"},
    ]

    def is_system_creator(self, request, view, action):
        instance = view.get_object()
        return request.user == instance.system_creator

    @classmethod
    def scope_queryset(cls, request, queryset):
        if request.user.is_superuser:
            logger.debug(f"Admin access granted for : {request.user}")
            return queryset
