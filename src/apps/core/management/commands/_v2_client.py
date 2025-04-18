import getpass
import logging
from argparse import ArgumentParser
from typing import Any, Iterator
from urllib import parse

import requests
from django.conf import settings

from apps.common.helpers import datetime_to_header
from apps.files.helpers import replace_query_param

logger = logging.getLogger(__name__)


class MigrationV2Client:
    """Metax V2 client for migration commands."""

    def __init__(self, options, stdout, stderr):
        self.ok = False
        self.metax_instance = None
        self.metax_user = None
        self.metax_password = None
        self.stdout = stdout
        self.stderr = stderr
        self.handle_metax_settings(options)

        # Sessions automatically use HTTP keep-alive which
        # avoids opening a new connection to Metax on each request.
        self.session = requests.Session()
        self.session.auth = self.metax_auth

    @property
    def metax_auth(self):
        if self.metax_user is None:
            return None
        return (self.metax_user, self.metax_password)

    def handle_metax_settings(self, options):
        if options.get("use_env"):
            self.metax_instance = settings.METAX_V2_HOST
            self.metax_user = settings.METAX_V2_USER
            self.metax_password = settings.METAX_V2_PASSWORD

        if instance := options.get("metax_instance"):
            self.metax_instance = instance

        if not self.metax_instance:
            self.stderr.write("Metax instance not specified.")
            return

        if options.get("prompt_credentials"):
            self.stdout.write(f"Please input credentials for {self.metax_instance}")
            self.metax_user = input("Username: ")
            self.metax_password = getpass.getpass("Password: ")

        if self.metax_instance:
            self.ok = True

    @classmethod
    def add_arguments(cls, parser: ArgumentParser):
        """Add V2 client specific arguments."""
        parser.add_argument(
            "--metax-instance",
            "-mi",
            type=str,
            required=False,
            help="Fully qualified Metax instance URL to migrate datasets from",
        )
        parser.add_argument(
            "--use-env",
            action="store_true",
            required=False,
            default=False,
            help="Read Metax instance and credentials from Django environment settings.",
        )
        parser.add_argument(
            "--prompt-credentials",
            action="store_true",
            required=False,
            default=False,
            help="Prompt Metax V2 credentials.",
        )

    def loop_pagination(self, response: requests.Response, batched=False) -> Iterator[Any]:
        """Request pages in a loop while yielding results."""
        while True:
            response.raise_for_status()
            response_json = response.json()
            if batched:
                yield response_json["results"]  # yield entire page as a list
            else:
                yield from response_json["results"]  # yield results one by one

            next_url = response_json.get("next")
            if not next_url:
                break
            response = self.session.get(next_url)

    def loop_cursor_pagination_with_id(
        self, response: requests.Response, batched=False
    ) -> Iterator[Any]:
        """Request pages using cursor pagination in a loop while yielding results.

        Assumes ordering=id and requires the V2 endpoint
        to support id__gt query parameter.
        """
        while True:
            response.raise_for_status()
            response_json = response.json()
            if batched:
                yield response_json["results"]  # yield entire page as a list
            else:
                yield from response_json["results"]  # yield results one by one

            next_url = response_json.get("next")
            if not next_url:
                break

            # Fetch only items that are newer than the last item on the previous page.
            # Unlike in offset pagination, adding or removing items during pagination
            # will not cause missing/duplicate items on the later pages.
            # This is also faster than offset pagination with large offsets.
            last_id = response_json["results"][-1]["id"]
            next_url = replace_query_param(next_url, "id__gt", last_id)
            next_url = replace_query_param(next_url, "offset", 0)
            response = self.session.get(next_url)

    def fetch_dataset_files(self, identifier: str) -> list:
        metax_instance = self.metax_instance
        response = self.session.get(
            f"{metax_instance}/rest/v2/datasets/{identifier}/files",
            params={
                "removed": "true",  # the dataset may be removed
            },
        )
        response.raise_for_status()
        files = response.json()

        # Fetch removed files
        response = self.session.get(
            f"{metax_instance}/rest/v2/datasets/{identifier}/files",
            params={
                "removed": "true",  # the dataset may be removed
                "removed_files": "true",  # return only removed files
            },
        )
        response.raise_for_status()
        files.extend(response.json())

        self.stdout.write(f"Found {len(files)} files for dataset {identifier}")
        return files

    def fetch_dataset_file_ids(self, identifier) -> list:
        metax_instance = self.metax_instance
        response = self.session.get(
            f"{metax_instance}/rest/v2/datasets/{identifier}/files",
            params={"removed": "true", "id_list": "true"},  # the dataset may be removed
        )
        response.raise_for_status()
        files = response.json()
        self.stdout.write(f"Found {len(files)} files for dataset {identifier}")
        return files

    def fetch_dataset(self, identifier, params={}) -> dict:
        metax_instance = self.metax_instance
        response = self.session.get(
            f"{metax_instance}/rest/v2/datasets/{identifier}",
            params={
                "include_editor_permissions": "true",
                "removed": "true",  # returns both removed and non-removed
                **params,
            },
        )
        response.raise_for_status()
        return response.json()

    def _fetch_files(self, params={}, batched=False, modified_since=None) -> Iterator[dict]:
        metax_instance = self.metax_instance
        headers = {}
        if modified_since:
            headers["If-Modified-Since"] = datetime_to_header(modified_since)
        response = self.session.get(
            f"{metax_instance}/rest/v2/files", params={**params, "ordering": "id"}, headers=headers
        )
        response.raise_for_status()
        removed = params.get("removed", "false")
        self.stdout.write(f"Found {response.json().get('count', 0)} files with removed={removed}")
        return self.loop_cursor_pagination_with_id(response, batched=batched)

    def fetch_files(self, params={}, batched=False, modified_since=None):
        yield from self._fetch_files(
            params={**params, "removed": "false"}, batched=batched, modified_since=modified_since
        )
        yield from self._fetch_files(
            params={**params, "removed": "true"}, batched=batched, modified_since=modified_since
        )

    def _fetch_contracts(self, params={}) -> Iterator[dict]:
        metax_instance = self.metax_instance
        headers = {}
        response = self.session.get(
            f"{metax_instance}/rest/v2/contracts",
            params={**params, "ordering": "id"},
            headers=headers,
        )
        response.raise_for_status()
        removed = params.get("removed", "false")
        self.stdout.write(
            f"Found {response.json().get('count', 0)} contracts with removed={removed}"
        )
        return self.loop_pagination(response, batched=False)

    def fetch_contracts(self, params={}):
        yield from self._fetch_contracts(params={**params, "removed": "false"})
        yield from self._fetch_contracts(params={**params, "removed": "true"})

    def _fetch_datasets(self, params={}, batched=False):
        metax_instance = self.metax_instance
        response = self.session.get(
            f"{metax_instance}/rest/v2/datasets",
            params={
                "include_editor_permissions": "true",
                "include_legacy": "true",
                **params,
            },
        )
        response.raise_for_status()
        removed = params.get("removed", "false")
        self.stdout.write(
            f"Found {response.json().get('count', 0)} datasets with removed={removed}"
        )
        return self.loop_pagination(response, batched=batched)

    def fetch_datasets(self, params={}, batched=False):
        yield from self._fetch_datasets(params={**params, "removed": "false"}, batched=batched)
        yield from self._fetch_datasets(params={**params, "removed": "true"}, batched=batched)

    def check_catalog(self, identifier):
        response = self.session.get(f"{self.metax_instance}/rest/datacatalogs/{identifier}")
        if response.status_code == 200:
            response_json = response.json()
            return response_json["catalog_json"]["identifier"]
