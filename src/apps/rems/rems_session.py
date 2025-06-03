import logging
from contextlib import contextmanager

import requests
from django.conf import settings
from requests.exceptions import HTTPError


logger = logging.getLogger(__name__)


class REMSError(HTTPError):
    pass


class REMSSession(requests.Session):
    """REMS wrapper for requests.Session.

    Modifies requests in the following way:
    - url is appended to REMS_BASE_URL
    - REMS headers are set automatically
    - raises error if request returns an error or is unsuccessful
    - when allow_notfound=True, a 404 response will not raise an error
    - as_user context manager allows making requests as another user
    """

    def __init__(self):
        super().__init__()
        self.base_url = settings.REMS_BASE_URL
        self.rems_user_id = settings.REMS_USER_ID
        self.rems_api_key = settings.REMS_API_KEY

    def get_headers(self):
        return {
            "x-rems-user-id": self.rems_user_id,
            "x-rems-api-key": self.rems_api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def request(
        self, method: str, url: str, allow_notfound=False, *args, **kwargs
    ) -> requests.Response:
        if not url.startswith("/"):
            raise ValueError("URL should start with '/'")
        request_url = f"{self.base_url}{url}"

        # Update the default headers with headers from kwargs
        headers = self.get_headers()
        if extra_headers := kwargs.get("headers"):
            headers.update(extra_headers)
        kwargs["headers"] = headers

        resp = super().request(method, request_url, *args, **kwargs)
        try:
            if resp.status_code == 404 and allow_notfound:
                return resp
            resp.raise_for_status()
        except HTTPError as e:
            logging.error(f"REMS error {str(e)}: {resp.text}")
            raise REMSError(*e.args, request=e.request, response=e.response)
        except Exception as e:
            logging.error(f"Making REMS request failed: {str(e)}")
            raise

        # Some errors may return a 200 response with success=False
        data = resp.json()
        if "success" in data and not data["success"]:
            logging.error(f"REMS error: {resp.text}")
            request_info = f"{resp.request.method} {url}"
            raise REMSError(
                f"REMS request '{request_info}' was unsuccessful, status_code={resp.status_code=}: {resp.text}",
                request=resp.request,
                response=resp,
            )
        return resp

    @contextmanager
    def as_user(self, user_id: str):
        """Make requests as a specific user instead of the REMS owner user.

        The request will have the same permissions as the user would.

        Example:
            # Get own applications of user
            session = REMSSession()
            with session.as_user("teppo"):
                applications = session.get("/api/my-applications").json()
        """
        original_user_id = self.rems_user_id
        try:
            self.rems_user_id = user_id
            yield
        finally:
            self.rems_user_id = original_user_id
