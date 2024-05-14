import json
import logging
from datetime import date, datetime

import requests
import urllib3
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import Signal, receiver
from rest_framework import exceptions, status

from apps.core.models import Dataset, FileSet
from apps.files.models import File
from apps.files.signals import pre_files_deleted

logger = logging.getLogger(__name__)

dataset_updated = Signal()
dataset_created = Signal()


class LegacyUpdateFailed(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT


@receiver(m2m_changed, sender=FileSet.files.through)
def handle_fileset_files_changed(sender, instance: FileSet, action, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return

    if action in ("post_remove", "post_clear"):
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
    res = requests.delete(url=f"{host}/{instance.id}", headers=headers, params=params)

    if res.status_code <= 204:
        logger.info(f"response form metax v2: {res}")
        return

    logger.warning(f"Syncing data with Metax v2 did not work properly: {res.content=}")


def fetch_dataset_from_v2(pid: str):
    host, headers = get_v2_request_settings()
    return requests.get(url=f"{host}?preferred_identifier={pid}", headers=headers)


def get_v2_request_settings():
    host = f"{settings.METAX_V2_HOST}/rest/v2/datasets"
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
        response = requests.get(url=f"{host}/{identifier}", headers=headers)
        found = response.status_code == 200

    res: requests.Response
    body = json.dumps(v2_dataset, cls=DjangoJSONEncoder)
    if found:
        res = requests.put(
            url=f"{host}/{identifier}?migration_override", data=body, headers=headers
        )
    else:
        res = requests.post(url=f"{host}?migration_override", data=body, headers=headers)
    if res.status_code in {200, 201}:
        logger.info(f"Sync {identifier} to V2: {res.status_code=}")
    else:
        logger.error(
            f"Sync {identifier} to V2 failed: {res.status_code=}:\n  {res.content=}, \n  {res.headers=}"
        )
        raise LegacyUpdateFailed(f"Failed to sync dataset ({identifier}) to Metax V2")


@receiver(dataset_updated)
def handle_dataset_updated(sender, data: Dataset, **kwargs):
    update_dataset_in_v2(data)


@receiver(dataset_created)
def handle_dataset_created(sender, data: Dataset, **kwargs):
    update_dataset_in_v2(data, created=True)
