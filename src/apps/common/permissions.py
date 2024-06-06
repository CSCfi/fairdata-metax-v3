import logging

from rest_access_policy import AccessPolicy

logger = logging.getLogger(__name__)


class DummyView:
    """Helper 'View' class to allow checking permissions for a specific object.

    DatasetAccessPolicy permission checks require a view that
    has "action" and "get_object" attributes.
    """

    def __init__(self, object=None, action: str = None):
        self.object = object
        self.action = action

    def get_object(self):
        return self.object


class DummyRequest:
    """Helper 'Request' class to allow checking permissions for a specific object.

    AccessPolicy permission checks require a request that
    has "user" and "method" attributes.
    """

    def __init__(self, user=None, method="") -> None:
        self.user = user
        self.method = method  # leave empty to avoid matching e.g. <method:get> rules


class BaseAccessPolicy(AccessPolicy):
    """Common base access policy class.

    For built-in special values that can be used in statements, see:
    https://rsinger86.github.io/drf-access-policy/statement_elements/

    For permissions of operations that don't directly map to a view action, use custom
    naming that won't clash with any potential action names, e.g. action="<op:download>".
    Permissions for custom operations can then be queried with query_object_permission.
    """

    id = "base-policy"
    admin_statements = [
        {"action": "*", "principal": "admin", "effect": "allow"},
    ]
    statements = [
        *admin_statements,
        {"action": ["list", "retrieve", "<safe_methods>"], "principal": "*", "effect": "allow"},
    ]

    def is_system_creator(self, request, view, action):
        instance = view.get_object()
        return request.user == instance.system_creator

    @classmethod
    def scope_queryset(cls, request, queryset):
        if request.user.is_superuser:
            logger.debug(f"Admin access granted for : {request.user}")
            return queryset

    def query_object_permission(self, user, object, action, method=""):
        """Helper method for querying for permissions of an object for current user.

        Normally has_permissions does not allow specifying object, action, or method
        directly. This function uses fake view and request objects to check for permissions
        without having to make an actual request.
        """
        view = DummyView(object=object, action=action)
        request = DummyRequest(user=user, method=method)
        return self.has_permission(request=request, view=view)
