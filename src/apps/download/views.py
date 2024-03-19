from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework import exceptions


class DownloadUnavailableException(exceptions.APIException):
    status_code = 503
    default_detail = "Download service unavailable."
    default_code = "service_unavailable"


class DownloadViewSet(ViewSet):
    def not_implemented_detail(self, endpoint_detail):
        return f"{endpoint_detail} through Metax V3 not implemented."

    @action(detail=False, methods=["get", "post"])
    def packages(self, request):
        """Placeholder for getting available packages and requesting package generation from download service."""
        if request.method == "GET":
            raise DownloadUnavailableException(
                detail=self.not_implemented_detail("Getting available packages")
            )
        else:
            raise DownloadUnavailableException(
            detail=self.not_implemented_detail("Requesting package generation")
        )

    @action(detail=False, methods=["post"])
    def authorize(self, request):
        """Placeholder for authorizing a resource for download from download service."""
        raise DownloadUnavailableException(
            detail=self.not_implemented_detail("Resource authorization")
        )

    @action(detail=False, methods=["post"])
    def subscribe(self, request):
        """Placeholder for subscribing to an email notification from download service when package creation is ready."""
        raise DownloadUnavailableException(
            detail=self.not_implemented_detail("Package subscriptions")
        )

    @action(detail=False, methods=["post"])
    def notifications(self, request):
        """Placeholder for sending package ready -notification to a subscriber"""
        raise DownloadUnavailableException(
            detail=self.not_implemented_detail("Package notifications")
        )
