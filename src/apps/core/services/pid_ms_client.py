import json
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

    def createURN(self, dataset_id):
        dummy_pid = "urn:nbn:fi:fd-dummy-" + str(uuid.uuid4())
        return dummy_pid

    def create_doi(self, dataset):
        _uuid = str(uuid.uuid4())
        dummy_pid = f"10.82614/{_uuid}"
        return dummy_pid


class _PIDMSClient:
    def __init__(self):
        self.pid_ms_url = f"https://{settings.PID_MS_BASEURL}"
        self.pid_ms_apikey = settings.PID_MS_APIKEY
        self.etsin_url = settings.ETSIN_URL

    def createURN(self, dataset_id):
        payload = {
            "url": f"https://{self.etsin_url}/dataset/{dataset_id}",
            "type": "URN",
            "persist": 0,
        }
        headers = {"apikey": self.pid_ms_apikey}
        try:
            response = requests.post(
                f"https://{settings.PID_MS_BASEURL}/v1/pid", json=payload, headers=headers
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError

    def create_doi(self, dataset_id):
        from apps.common.datacitedata import Datacitedata

        payload = Datacitedata().get_datacite_json(dataset_id)
        payload["data"]["attributes"]["event"] = "publish"
        payload["data"]["attributes"]["url"] = f"https://{self.etsin_url}/dataset/{dataset_id}"
        headers = {"apikey": self.pid_ms_apikey, "Content-Type": "application/json"}
        try:
            response = requests.post(
                f"https://{settings.PID_MS_BASEURL}/v1/pid/doi", json=payload, headers=headers
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError


class ServiceUnavailableError(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


class PIDMSClient:
    def createURN(self, dataset_id):
        _client = import_string(settings.PID_MS_CLIENT_INSTANCE)()
        return _client.createURN(dataset_id)

    def create_doi(self, dataset_id):
        _client = import_string(settings.PID_MS_CLIENT_INSTANCE)()
        return _client.create_doi(dataset_id)
