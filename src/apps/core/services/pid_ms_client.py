import json
import logging
import uuid

import requests
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import status
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

    def create_doi(self, dataset_id):
        _uuid = str(uuid.uuid4())
        dummy_pid = f"10.82614/{_uuid}"
        return dummy_pid

    def update_doi_dataset(self, dataset_id, doi):
        _uuid = str(uuid.uuid4())
        dummy_url = "http://localhost/a"
        return dummy_url


class _PIDMSClient:
    def __init__(self):
        self.pid_ms_url = f"https://{settings.PID_MS_BASEURL}"
        self.etsin_url = settings.ETSIN_URL
        self.headers = {"apikey": settings.PID_MS_APIKEY}

    def create_urn(self, dataset_id):
        payload = {
            "url": f"https://{self.etsin_url}/dataset/{dataset_id}",
            "type": "URN",
            "persist": 0,
        }
        try:
            response = requests.post(
                f"https://{settings.PID_MS_BASEURL}/v1/pid", json=payload, headers=self.headers
            )
            response.raise_for_status()
            if not response.text:
                raise Exception(f"PID MS returned: {response.text}")
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError

    def create_doi(self, dataset_id):
        from apps.common.datacitedata import Datacitedata

        payload = Datacitedata().get_datacite_json(dataset_id)
        payload["data"]["attributes"]["event"] = "publish"
        payload["data"]["attributes"]["url"] = f"https://{self.etsin_url}/dataset/{dataset_id}"
        try:
            response = requests.post(
                f"https://{settings.PID_MS_BASEURL}/v1/pid/doi", json=payload, headers=self.headers
            )
            response.raise_for_status()
            if not response.text:
                raise Exception(f"PID MS returned: {response.text}")
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError

    def update_doi_dataset(self, dataset_id, doi):
        # DOI might not exist in PID MS if the dataset was created in Metax V2
        if not self.check_if_doi_exists(dataset_id, doi):
            self.insert_pid(dataset_id, doi)

        from apps.common.datacitedata import Datacitedata

        payload = Datacitedata().get_datacite_json(dataset_id)
        payload["data"]["attributes"]["url"] = f"https://{self.etsin_url}/dataset/{dataset_id}"
        try:
            response = requests.put(
                f"https://{settings.PID_MS_BASEURL}/v1/pid/doi/{doi}",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError

    def check_if_doi_exists(self, dataset_id, doi):
        dataset_url = f"https://{self.etsin_url}/dataset/{dataset_id}"
        try:
            response = requests.get(
                f"https://{settings.PID_MS_BASEURL}/get/v1/pid/{doi}",
                headers=self.headers,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return False

            response.raise_for_status()

            if response.text != dataset_url:
                raise Exception(
                    f"Dataset url ({dataset_url}) doesn't match in PID MS: {response.text}"
                )
            return True
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}")
            raise ServiceUnavailableError

    def insert_pid(self, dataset_id, pid):
        payload = {"URL": f"https://{self.etsin_url}/dataset/{dataset_id}"}

        try:
            _logger.info(f"Inserting PID {pid} to PID-MS")
            response = requests.post(
                f"https://{settings.PID_MS_BASEURL}/v1/pid/{pid}",
                json=payload,
                headers=self.headers,
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
    def create_urn(self, dataset_id):
        _client = import_string(settings.PID_MS_CLIENT_INSTANCE)()
        return _client.create_urn(dataset_id)

    def create_doi(self, dataset_id):
        _client = import_string(settings.PID_MS_CLIENT_INSTANCE)()
        doi = _client.create_doi(dataset_id)
        doi_value = f"doi:{doi}"
        return doi_value

    def update_doi_dataset(self, dataset_id, doi):
        _client = import_string(settings.PID_MS_CLIENT_INSTANCE)()
        if doi.startswith("doi:"):
            doi = doi.replace("doi:", "")
        return _client.update_doi_dataset(dataset_id, doi)
