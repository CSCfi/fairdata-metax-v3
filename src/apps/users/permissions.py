from apps.common.permissions import BaseAccessPolicy


class UsersViewAccessPolicy(BaseAccessPolicy):
    statements = [
        {
            "action": ["<safe_methods>", "delete_data"],
            "principal": "group:service",
            "effect": "allow",
        },
        {"action": "*", "principal": "admin", "effect": "allow"},
    ]
