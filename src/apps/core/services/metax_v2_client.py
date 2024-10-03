import json
import logging
from typing import TYPE_CHECKING

import requests
import urllib3
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from rest_framework import exceptions, status

if TYPE_CHECKING:
    # Allow using "Dataset" in type hints while avoiding circular import errors
    from apps.core.models import Dataset


logger = logging.getLogger(__name__)


class LegacyUpdateFailed(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT


class MetaxV2Client:
    """Client for updating datasets in V2."""

    def __init__(self):
        self.host = f"{settings.METAX_V2_HOST}/rest/v2"
        self.headers = urllib3.make_headers(
            basic_auth=f"{settings.METAX_V2_USER}:{settings.METAX_V2_PASSWORD}",
        )
        self.headers["Content-Type"] = "application/json"
        self.headers["Accept"] = "application/json"

    def delete_dataset(self, instance: "Dataset", soft=False):
        """Sync Metax V2 when deleting dataset from v3"""

        params = {"removed": "true", "hard": "true"}

        if soft or instance.state == instance.StateChoices.DRAFT:
            params["hard"] = None  # Drafts are hard deleted implicitly

        res = requests.delete(
            url=f"{self.host}/datasets/{instance.id}", headers=self.headers, params=params
        )

        if res.status_code <= 204:
            logger.info(f"Deleted {instance.id} from Metax v2: {res}")
            return

        logger.warning(f"Failed to delete dataset {instance.id} from Metax v2: {res.content=}")

    def _patch_api_meta(self, dataset: "Dataset") -> requests.Response:
        """Patch dataset api_meta to version 3."""
        body = {"identifier": str(dataset.id), "api_meta": {"version": 3}}
        return requests.patch(
            url=f"{self.host}/datasets/{dataset.id}", json=body, headers=self.headers
        )

    def update_api_meta(self, dataset: "Dataset"):
        """Mark a published dataset as V3 dataset.

        Setting the api version to 3 will prevent further modifications
        to the dataset using the V2 API.
        """
        if dataset.state != "published":
            raise ValueError("Dataset is not published")

        if dataset._state.adding:
            raise ValueError("Dataset is not saved")

        if dataset.api_version >= 3:
            return  # API version already V3, no need to update

        res = self._patch_api_meta(dataset)
        if res.status_code == 200:
            # Update only api_version, avoid side-effects from Dataset.save
            dataset.api_version = 3
            models.Model.save(dataset, update_fields=["api_version"])
            logger.info(f"Marked published dataset {dataset.id} as a V3 dataset")
        else:
            logger.warning(
                f"Failed to mark {dataset.id} as V3 dataset: "
                f"{res.status_code=}:\n  {res.content=}"
            )

    def update_draft_api_meta(self, dataset: "Dataset"):
        """Mark a draft dataset as modified in V3.

        Dataset drafts from V3 are not synced to V2, but if a draft
        has been migrated from V2, any modifications to it in V3
        should make it non-modifiable using the V2 API.
        """
        if dataset.state != "draft":
            raise ValueError("Dataset is not a draft")

        if dataset._state.adding:
            raise ValueError("Dataset is not saved")

        if legacy := getattr(dataset, "legacydataset", None):
            version = legacy.dataset_json.get("api_meta", {}).get("version", 0)
            if version < 3:
                res = self._patch_api_meta(dataset)
                if res.status_code == 200:
                    # Update api version in dataset_json
                    legacy.dataset_json["api_meta"] = {"version": 3}
                    legacy.save(update_fields=["dataset_json"])
                    logger.info(f"Marked draft {dataset.id} as a V3 dataset")
                else:
                    logger.warning(
                        f"Failed to mark draft {dataset.id} as V3 dataset: "
                        f"{res.status_code=}:\n  {res.content=}"
                    )

        # Mark the original version as having been modified in V3
        if dataset.draft_of:
            self.update_api_meta(dataset.draft_of)

    def update_dataset(self, dataset: "Dataset", created=False):
        if dataset.state != "published":
            self.update_draft_api_meta(dataset)
            return

        if dataset.removed or dataset.api_version < 3:
            return

        v2_dataset = dataset.as_v2_dataset()
        identifier = v2_dataset["identifier"]

        found = False
        if not created:
            response = requests.get(url=f"{self.host}/datasets/{identifier}", headers=self.headers)
            found = response.status_code == 200

        res: requests.Response
        body = json.dumps(v2_dataset, cls=DjangoJSONEncoder)
        if found:
            res = requests.put(
                url=f"{self.host}/datasets/{identifier}?migration_override",
                data=body,
                headers=self.headers,
            )
        else:
            res = requests.post(
                url=f"{self.host}/datasets?migration_override", data=body, headers=self.headers
            )
        if res.status_code in {200, 201}:
            logger.info(f"Sync {identifier} to V2: {res.status_code=}")
        else:
            logger.error(
                f"Sync {identifier} to V2 failed: {res.status_code=}:\n"
                f"  {res.content=}, \n  {res.headers=}"
            )
            raise LegacyUpdateFailed(f"Failed to sync dataset ({identifier}) to Metax V2")

    def update_dataset_files(self, dataset: "Dataset", created=False):
        fileset = getattr(dataset, "file_set", None)
        if not fileset:
            return

        if dataset.state != "published" or dataset.removed or dataset.api_version < 3:
            return

        identifier = dataset.id
        metadata = {
            "files": [d.to_legacy() for d in fileset.file_metadata.all()],
            "directories": [d.to_legacy() for d in fileset.directory_metadata.all()],
        }

        missing_legacy = fileset.files.filter(legacy_id__isnull=True)
        if missing_legacy_count := missing_legacy.count():
            logger.error(f"{missing_legacy_count} files are missing legacy_id, not syncing to V2")
            raise LegacyUpdateFailed(f"Failed to sync dataset {identifier} files to Metax V2")

        legacy_ids = list(fileset.files.values_list("legacy_id", flat=True))
        if created and not legacy_ids:
            return  # New dataset with no files to sync

        data = {"file_ids": legacy_ids, "user_metadata": metadata}

        res = requests.post(
            url=f"{self.host}/datasets/{identifier}/files_from_v3", json=data, headers=self.headers
        )
        if res.status_code == 200:
            logger.info(f"Sync {identifier} files to V2: {res.status_code=}")
        else:
            logger.error(
                f"Sync {identifier} files to V2 failed: {res.status_code=}:"
                f"\n  {res.content=}, \n  {res.headers=}"
            )
            raise LegacyUpdateFailed(f"Failed to sync dataset {identifier} files to Metax V2")