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
        elif request.user.groups.filter(name="ida").exists():
            return queryset
        else:
            return queryset.filter(file_sets__dataset__state="published")
