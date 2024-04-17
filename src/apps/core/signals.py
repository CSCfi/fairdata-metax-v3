import json
import logging
from datetime import date, datetime

import requests
import urllib3
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import Signal, receiver

from apps.core.models import Dataset, FileSet

logger = logging.getLogger(__name__)

dataset_updated = Signal()
dataset_created = Signal()


@receiver(m2m_changed, sender=FileSet.files.through)
def handle_files_changed(sender, instance: FileSet, action, **kwargs):
    if instance.skip_files_m2m_changed:  # allow skipping handler
        return

    if action in ("post_remove", "post_clear"):
        instance.remove_unused_file_metadata()


@receiver(post_delete, sender=Dataset)
def delete_dataset_from_v2(sender, instance: Dataset, **kwargs):
    """Sync Metax V2 when deleting dataset from v3"""
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    host, headers = get_v2_request_settings()
    res = requests.delete(url=f"{host}/{instance.id}", headers=headers)

    if res.status_code <= 204:
        logger.info(f"response form metax v2: {res}")
        return

    logger.warning(f"Syncing data with Metax v2 did not work properly: {res}")


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


@receiver(dataset_updated)
def update_dataset_in_v2(sender, data: Dataset, **kwargs):
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    if data.state != "published":
        return

    v2_dataset = data.as_v2_dataset()
    identifier = v2_dataset["identifier"]
    body = json.dumps(v2_dataset, cls=DjangoJSONEncoder)
    host, headers = get_v2_request_settings()

    try:
        response = requests.get(url=f"{host}/{identifier}", headers=headers)
        logger.info(f"{response.status_code=}")
        if response.status_code == 200:
            res = requests.put(url=f"{host}/{identifier}", data=body, headers=headers)
            logger.info(f"{res.status_code=}: {res.content=}, {res.headers=}")
        elif v2_dataset["api_meta"]["version"] == 3 and v2_dataset["research_dataset"].get(
            "preferred_identifier"
        ):
            res = requests.post(url=f"{host}?migration_override", data=body, headers=headers)
            logger.info(f"{res.status_code=}: {res.content=}, {res.headers=}")
        else:
            logger.warning(
                f"could not sync dataset ({identifier}), because it was not found in Metax v2"
            )

    except Exception as e:
        logger.exception(e)


@receiver(dataset_created)
def create_dataset_to_v2(sender, data: Dataset, **kwargs):
    if not settings.METAX_V2_INTEGRATION_ENABLED:
        return

    if data.state != "published":
        return

    v2_dataset = data.as_v2_dataset()
    if hasattr(v2_dataset["research_dataset"], "issued"):
        v2_dataset["research_dataset"]["issued"] = v2_dataset["research_dataset"]["issued"].date()
    body = json.dumps(v2_dataset, cls=DjangoJSONEncoder)
    host, headers = get_v2_request_settings()
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    try:
        if v2_dataset["api_meta"]["version"] == 3 and v2_dataset["research_dataset"].get(
            "preferred_identifier"
        ):
            res = requests.post(url=f"{host}?migration_override", data=body, headers=headers)
            logger.info(f"{res.status_code=}: {res.content=}, {res.headers=}")

    except Exception as e:
        logger.exception(e)
