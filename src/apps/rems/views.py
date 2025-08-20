from django.conf import settings
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import exceptions

from apps.common.views import QueryParamsMixin
from apps.rems.rems_service import REMSService
from apps.rems.rems_session import REMSError


class REMSApplicationsViewSet(QueryParamsMixin, ViewSet):
    def check_rems_request(self, request):
        if not settings.REMS_ENABLED:
            raise exceptions.MethodNotAllowed(method=request.method, detail="REMS is not enabled")
        if not getattr(request.user, "fairdata_username", None):
            raise exceptions.PermissionDenied(
                detail="You need to be logged in as a Fairdata user."
            )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a REMS application by id."""
        self.check_rems_request(request)
        try:
            application_id = int(kwargs["pk"])
        except ValueError:
            raise exceptions.ValidationError(detail="Invalid application id")

        try:
            service = REMSService()
            return Response(
                data=service.get_user_application(request.user, application_id=application_id)
            )
        except REMSError as err:
            if err.response.status_code == 404:
                raise exceptions.NotFound("Application not found")
            raise

    def list(self, request, *args, **kwargs):
        """List all REMS applications user can see."""
        self.check_rems_request(request)
        service = REMSService()
        return Response(data=service.get_user_applications(request.user))

    @action(detail=False, url_path="todo")
    def list_todo(self, request, *args, **kwargs):
        """List REMS applications user needs to act on."""
        self.check_rems_request(request)
        service = REMSService()
        return Response(data=service.get_user_applications_todo(request.user))

    @action(detail=False, url_path="handled")
    def list_handled(self, request, *args, **kwargs):
        """List REMS applications user no longer needs to act on."""
        self.check_rems_request(request)
        service = REMSService()
        return Response(data=service.get_user_applications_handled(request.user))
