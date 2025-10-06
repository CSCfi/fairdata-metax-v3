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

    def _validate_response_status(self, response: requests.Response):
        """Raise errors for unexpected status codes."""
        response.raise_for_status()
        if response.status_code < 100:
            raise requests.HTTPError(
                f"Invalid status code {response.status_code} in response: {response.text}"
            )

    def _validate_pid(self, dataset_id, prefix: str, identifier: str):
        """Raise error if identifier from PID MS does not match expected prefix."""
        if not identifier.startswith(prefix):
            raise Exception(
                f"PID MS returned invalid {identifier=} for {dataset_id=}, expected {prefix=}"
            )

    def create_urn(self, dataset_id):
        payload = {
            "url": f"https://{self.etsin_url}/dataset/{dataset_id}",
            "type": "URN",
            "persist": 0,
        }
        url = f"https://{settings.PID_MS_BASEURL}/v1/pid"
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            self._validate_response_status(response)
            self._validate_pid(dataset_id, prefix="urn:", identifier=response.text)
            _logger.info(f"Created URN for dataset {dataset_id}: {response.text}")
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}, request: POST {url}, payload={payload}")
            raise ServiceUnavailableError

    def create_doi(self, dataset_id):
        payload = self.get_datacite_payload(dataset_id)
        payload["data"]["attributes"]["event"] = "publish"
        payload["data"]["attributes"]["url"] = f"https://{self.etsin_url}/dataset/{dataset_id}"
        url = f"https://{settings.PID_MS_BASEURL}/v1/pid/doi"
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            self._validate_response_status(response)
            self._validate_pid(
                dataset_id, prefix=settings.PID_MS_DOI_PREFIX, identifier=response.text
            )
            _logger.info(f"Created DOI for dataset {dataset_id}: {response.text}")
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}, request: POST {url}, payload={payload}")
            raise ServiceUnavailableError

    def get_datacite_payload(self, dataset_id):
        from apps.core.models import Dataset
        from apps.common.datacitedata import Datacitedata

        dataset = Dataset.objects.get(id=dataset_id)
        datacite_json = Datacitedata().get_datacite_json(dataset)
        return {"data": {"type": "dois", "attributes": datacite_json}}

    def update_doi_dataset(self, dataset_id, doi):
        # DOI might not exist in PID MS if the dataset was created in Metax V2
        if not self.check_if_doi_exists(dataset_id, doi):
            self.insert_pid(dataset_id, doi)

        payload = self.get_datacite_payload(dataset_id)
        payload["data"]["attributes"]["url"] = f"https://{self.etsin_url}/dataset/{dataset_id}"
        url = f"https://{settings.PID_MS_BASEURL}/v1/pid/doi/{doi}"
        try:
            response = requests.put(
                url,
                json=payload,
                headers=self.headers,
            )
            self._validate_response_status(response)
            _logger.info(f"Updated DOI dataset {dataset_id}: {response.text}")
            return response.text
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}, request: PUT {url}, payload={payload}")
            raise ServiceUnavailableError

    def check_if_doi_exists(self, dataset_id, doi):
        dataset_url = f"https://{self.etsin_url}/dataset/{dataset_id}"
        url = f"https://{settings.PID_MS_BASEURL}/get/v1/pid/{doi}"
        try:
            response = requests.get(
                url=url,
                headers=self.headers,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return False

            self._validate_response_status(response)
            if response.text != dataset_url:
                raise Exception(
                    f"Dataset url ({dataset_url}) doesn't match in PID MS: {response.text}"
                )
            return True
        except Exception as e:
            _logger.error(f"Exception in PIDMSClient: {e}, request: GET {url}")
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
            self._validate_response_status(response)
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
