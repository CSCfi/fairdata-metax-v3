import logging
import uuid

import requests
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException

_logger = logging.getLogger(__name__)


# Dummy client that is used when running Metax-service in development environment
# Doesn't connect anywhere, but instead gives dummy values
class _DummyPIDMSClient:
    def __init__(self):
        # Empty constructor
        pass

    def create_urn(self, dataset_id):
        dummy_pid = "urn:nbn:fi:fd-dummy-" + str(uuid.uuid4())
        return dummy_pid


class _PIDMSClient:
    def __init__(self):
        self.pid_ms_url = f"https://{settings.PID_MS_BASEURL}"
        self.pid_ms_apikey = settings.PID_MS_APIKEY
        self.etsin_url = settings.ETSIN_URL

    def create_urn(self, dataset_id):
        payload = {
            "url": f"https://{self.etsin_url}/dataset/{dataset_id}",
            "type": "URN",
            "persist": 0,
        }
        headers = {"apikey": self.pid_ms_apikey}
        try:
            response = requests.post(self.pid_ms_url + "/v1/pid", json=payload, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError


class ServiceUnavailableError(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


PIDMSClient = import_string(settings.PID_MS_CLIENT_INSTANCE)()
