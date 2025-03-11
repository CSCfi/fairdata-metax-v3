from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from watchman.decorators import check

from apps.core.models.sync import V2SyncStatus

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
