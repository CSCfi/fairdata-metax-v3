from django.conf import settings
from rest_framework import exceptions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.common.serializers.fields import CommaSeparatedListField
from apps.common.views import CommonViewSet
from apps.rems.rems_service import REMSService
from apps.rems.rems_session import REMSError
from apps.rems.serializers import ApplicationCommandSerializer


class RolesQueryParamsSerializer(serializers.Serializer):
    roles = CommaSeparatedListField(
        child=serializers.ChoiceField(choices=["applicant", "handler"]), default=None
    )


class REMSApplicationsViewSet(CommonViewSet):
    query_serializers = [
        {"class": RolesQueryParamsSerializer, "actions": ["list"]},
    ]

    def check_rems_request(self, request):
        if not settings.REMS_ENABLED:
            raise exceptions.MethodNotAllowed(method=request.method, detail="REMS is not enabled")
        if not getattr(request.user, "fairdata_username", None):
            raise exceptions.PermissionDenied(
                detail="You need to be logged in as a Fairdata user."
            )

    def parse_application_id(self, application_id: str) -> int:
        try:
            return int(application_id)
        except ValueError:
            raise exceptions.ValidationError(detail="Invalid application id")

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a REMS application by id."""
        self.check_rems_request(request)
        application_id = self.parse_application_id(kwargs["pk"])

        try:
            service = REMSService()
            return Response(
                data=service.get_user_application(request.user, application_id=application_id)
            )
        except REMSError as err:
            if err.response is not None and err.response.status_code == 404:
                raise exceptions.NotFound("Application not found")
            raise

    def _get_application_command_comment(self, request) -> str:
        if not request.data:
            return ""
        serializer = ApplicationCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["comment"]

    @swagger_auto_schema(request_body=ApplicationCommandSerializer)
    @action(detail=True, url_path="approve", methods=["post"])
    def approve(self, request, *args, **kwargs):
        """Approve a REMS application."""
        self.check_rems_request(request)
        application_id = self.parse_application_id(kwargs["pk"])

        service = REMSService()
        try:
            comment = self._get_application_command_comment(request)
            data = service.approve_application(request.user, application_id=application_id, comment=comment)
        except REMSError as err:
            if err.is_forbidden:
                raise exceptions.PermissionDenied(
                    detail="You are not allowed to perform this action"
                )
            raise
        return Response(data=data)

    @swagger_auto_schema(request_body=ApplicationCommandSerializer)
    @action(detail=True, url_path="reject", methods=["post"])
    def reject(self, request, *args, **kwargs):
        """Reject a REMS application."""
        self.check_rems_request(request)
        application_id = self.parse_application_id(kwargs["pk"])

        service = REMSService()
        try:
            comment = self._get_application_command_comment(request)
            data = service.reject_application(request.user, application_id=application_id, comment=comment)
        except REMSError as err:
            if err.is_forbidden:
                raise exceptions.PermissionDenied(
                    detail="You are not allowed to perform this action"
                )
            raise
        return Response(data=data)

    @swagger_auto_schema(request_body=ApplicationCommandSerializer)
    @action(detail=True, url_path="close", methods=["post"])
    def close(self, request, *args, **kwargs):
        """Close a submitted or approved REMS application."""
        self.check_rems_request(request)
        application_id = self.parse_application_id(kwargs["pk"])

        service = REMSService()
        try:
            comment = self._get_application_command_comment(request)
            data = service.close_application(request.user, application_id=application_id, comment=comment)
        except REMSError as err:
            if err.is_forbidden:
                raise exceptions.PermissionDenied(
                    detail="You are not allowed to perform this action"
                )
            raise
        return Response(data=data)

    def list(self, request, *args, **kwargs):
        """List all REMS applications user can see."""
        self.check_rems_request(request)
        service = REMSService()
        applications = service.get_user_applications(
            request.user, roles=self.query_params["roles"]
        )
        return Response(data=applications)

    @action(detail=False, url_path="todo")
    def list_todo(self, request, *args, **kwargs):
        """List received REMS applications user needs to act on."""
        self.check_rems_request(request)
        service = REMSService()
        applications = service.get_user_applications_todo(request.user)
        return Response(data=applications)

    @action(detail=False, url_path="handled")
    def list_handled(self, request, *args, **kwargs):
        """List received REMS applications user no longer needs to act on."""
        self.check_rems_request(request)
        service = REMSService()
        applications = service.get_user_applications_handled(request.user)
        return Response(data=applications)
