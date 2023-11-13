from apps.common.permissions import BaseAccessPolicy


class FilesAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["group:ida"],
            "effect": "allow",
        },
    ] + BaseAccessPolicy.statements

    @classmethod
    def scope_queryset(cls, request, queryset):
        if q := super().scope_queryset(request, queryset):
            return q
        elif request.user.is_anonymous:
            return queryset.filter(file_sets__dataset__state="published")
        elif "ida" in request.user.groups.all():
            return queryset
