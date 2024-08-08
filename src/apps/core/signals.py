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

from apps.core.models import Dataset, FileSet
from apps.core.models.file_metadata import FileSetDirectoryMetadata, FileSetFileMetadata
from apps.files.models import File
from apps.files.signals import pre_files_deleted

logger = logging.getLogger(__name__)

dataset_updated = Signal()
dataset_created = Signal()


class LegacyUpdateFailed(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT


@receiver(m2m_changed, sender=FileSet.files.through)
def handle_fileset_files_changed(sender, instance: FileSet, action, pk_set, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return
    if action == "post_add":
        instance.update_published()
    elif action == "pre_clear":
        instance.update_published(exclude_self=True)
    elif action == "pre_remove":
        instance.update_published(queryset=instance.files.filter(id__in=pk_set), exclude_self=True)
    elif action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()


@receiver(pre_files_deleted, sender=File)
def handle_files_deleted(sender, queryset, **kwargs):
    fileset_ids = queryset.values_list("file_sets").order_by().distinct()
    for fileset in FileSet.all_objects.filter(id__in=fileset_ids):
        fileset.deprecate_dataset()


@receiver(post_delete, sender=Dataset)
def delete_dataset_from_v2(sender, instance: Dataset, **kwargs):
    """Sync Metax V2 when deleting dataset from v3"""
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    params = {"removed": "true", "hard": "true"}

    if "soft" in kwargs and kwargs["soft"] is True:
        params["hard"] = None

    host, headers = get_v2_request_settings()
    res = requests.delete(url=f"{host}/datasets/{instance.id}", headers=headers, params=params)

    if res.status_code <= 204:
        logger.info(f"response form metax v2: {res}")
        return

    logger.warning(f"Syncing data with Metax v2 did not work properly: {res.content=}")


def fetch_dataset_from_v2(pid: str):
    host, headers = get_v2_request_settings()
    return requests.get(url=f"{host}/datasets?preferred_identifier={pid}", headers=headers)


def get_v2_request_settings():
    host = f"{settings.METAX_V2_HOST}/rest/v2"
    headers = urllib3.make_headers(
        basic_auth=f"{settings.METAX_V2_USER}:{settings.METAX_V2_PASSWORD}",
    )
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    return host, headers


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def update_dataset_in_v2(dataset: Dataset, created=False):
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    if dataset.state != "published" or dataset.removed or dataset.api_version < 3:
        return

    v2_dataset = dataset.as_v2_dataset()
    identifier = v2_dataset["identifier"]

    host, headers = get_v2_request_settings()

    found = False
    if not created:
        response = requests.get(url=f"{host}/datasets/{identifier}", headers=headers)
        found = response.status_code == 200

    res: requests.Response
    body = json.dumps(v2_dataset, cls=DjangoJSONEncoder)
    if found:
        res = requests.put(
            url=f"{host}/datasets/{identifier}?migration_override", data=body, headers=headers
        )
    else:
        res = requests.post(url=f"{host}/datasets?migration_override", data=body, headers=headers)
    if res.status_code in {200, 201}:
        logger.info(f"Sync {identifier} to V2: {res.status_code=}")
    else:
        logger.error(
            f"Sync {identifier} to V2 failed: {res.status_code=}:\n  {res.content=}, \n  {res.headers=}"
        )
        raise LegacyUpdateFailed(f"Failed to sync dataset ({identifier}) to Metax V2")


def update_dataset_files_in_v2(dataset: Dataset, created=False):
    fileset = getattr(dataset, "file_set", None)
    if not fileset:
        return

    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    if dataset.state != "published" or dataset.removed or dataset.api_version < 3:
        return

    identifier = dataset.id
    host, headers = get_v2_request_settings()

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
        url=f"{host}/datasets/{identifier}/files_from_v3", json=data, headers=headers
    )
    if res.status_code == 200:
        logger.info(f"Sync {identifier} files to V2: {res.status_code=}")
    else:
        logger.error(
            f"Sync {identifier} files to V2 failed: {res.status_code=}:\n  {res.content=}, \n  {res.headers=}"
        )
        raise LegacyUpdateFailed(f"Failed to sync dataset {identifier} files to Metax V2")


@receiver(dataset_updated)
def handle_dataset_updated(sender, data: Dataset, **kwargs):
    if data.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(data, "file_set", None)
    ):
        fileset.update_published()
    update_dataset_in_v2(data)
    update_dataset_files_in_v2(data)


@receiver(dataset_created)
def handle_dataset_created(sender, data: Dataset, **kwargs):
    if data.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(data, "file_set", None)
    ):
        fileset.update_published()
    update_dataset_in_v2(data, created=True)
    update_dataset_files_in_v2(data, created=True)


@receiver(pre_delete, sender=Dataset)
def handle_dataset_pre_delete(sender, instance: Dataset, **kwargs):
    if instance.state == Dataset.StateChoices.PUBLISHED and (
        fileset := getattr(instance, "file_set", None)
    ):
        fileset.update_published(exclude_self=True)
