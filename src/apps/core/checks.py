from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from watchman.decorators import check

from apps.core.models import Dataset
from apps.core.models.access_rights import AccessTypeChoices
from apps.core.models.sync import V2SyncStatus
from apps.rems.models import REMSCatalogueItem

sync_stall_threshold = timedelta(minutes=5)


@check
def _check_v2_sync():
    """Check for failed dataset synchronization to V2."""
    q_error = Q(error__isnull=False)
    q_stalled = Q(
        sync_started__lt=timezone.now() - sync_stall_threshold, sync_stopped__isnull=True
    )
    fails = V2SyncStatus.objects.filter(q_error | q_stalled).distinct()
    fail_counts = {
        action["action"]: action["count"]
        for action in fails.values("action").annotate(count=Count("*")).order_by("action")
    }
    if fails:
        return {"ok": False, "fails": fail_counts}

    return {"ok": True}


def check_v2_sync():
    return {"sync_to_v2": _check_v2_sync()}


@check
def _check_rems_publish():
    """Check for failed dataset publication to REMS."""
    if fail_count := Dataset.objects.filter(rems_publish_error__isnull=False).count():
        return {"ok": False, "fails": fail_count}
    return {"ok": True}


def check_rems_publish():
    if not settings.REMS_ENABLED:
        return {}
    return {"rems_publish": _check_rems_publish()}
