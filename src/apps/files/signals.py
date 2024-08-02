import json
import logging
from datetime import date, datetime
from typing import List

import requests
import urllib3
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import m2m_changed, post_delete, pre_delete
from django.dispatch import Signal, receiver
from rest_framework import exceptions, status

from apps.files.models import File

logger = logging.getLogger(__name__)

# Sent when files are deleted using the API, list of deleted files provided in `queryset` argument
pre_files_deleted = Signal()

# Send when files are created, modified or deleted. Used for triggering file synchronization to V2.
# Expects list of {"object": File, "action": "insert"/"update"/"delete"}
sync_files = Signal()


class LegacyFileUpdateFailed(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT


def get_v2_request_settings():
    host = f"{settings.METAX_V2_HOST}/rest/v2"
    headers = urllib3.make_headers(
        basic_auth=f"{settings.METAX_V2_USER}:{settings.METAX_V2_PASSWORD}",
    )
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    return host, headers


@receiver(sync_files)
def handle_sync_files(sender, actions: List[dict], **kwargs):
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    to_legacy = []
    files_without_legacy_ids = {}
    for file_action in actions:
        file: File = file_action["object"]
        if file.legacy_id is None:
            files_without_legacy_ids[(file.storage_service, file.storage_identifier)] = file
        to_legacy.append(file.to_legacy_sync())

    host, headers = get_v2_request_settings()
    body = json.dumps(to_legacy, cls=DjangoJSONEncoder)
    res = requests.post(url=f"{host}/files/sync_from_v3", data=body, headers=headers)
    if res.status_code in {200, 201}:
        logger.info(f"Synced {len(to_legacy)} files to V2")
    else:
        logger.error(
            f"Syncing files to V2 failed: {res.status_code=}:\n  {res.content=}, \n  {res.headers=}"
        )
        raise LegacyFileUpdateFailed("Failed to sync files to Metax V2")

    # Fill in missing legacy_ids from response data
    for v2_file in res.json():
        v3_storage = settings.LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE[v2_file["file_storage"]]
        if file := files_without_legacy_ids.get((v3_storage, v2_file["identifier"])):
            file.legacy_id = v2_file["id"]

    for key, file in files_without_legacy_ids.items():
        if file.legacy_id is None:
            logger.warn(f"Sync error: file {key} did not get a legacy id")

    # Update legacy_id values for files that didn't have one yet
    files_with_new_legacy_ids = [f for f in files_without_legacy_ids.values() if f.legacy_id]
    File.all_objects.bulk_update(files_with_new_legacy_ids, fields=["legacy_id"], batch_size=2000)
