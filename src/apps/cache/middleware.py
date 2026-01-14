from collections import defaultdict
import logging

from cachalot.cache import cachalot_caches
from cachalot.api import invalidate

logger = logging.getLogger(__name__)


class CachalotClearMiddleware:
    """Ensure per-thread cachalot cache is empty after request.

    Mitigates cachalot bug where the per-thread internal cache
    may persist data across requests.
    See https://github.com/noripyt/django-cachalot/issues/278

    Should inserted before any middleware that makes DB requests that
    may be cached in cachalot.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # The atomic_caches dict contains per-database lists of cache dicts
        # that will be committed to the cache backend at the end of the transaction.
        # The dict should not contain any non-empty lists at after a request.
        atomic_caches: defaultdict[str, list] = cachalot_caches.atomic_caches
        if any(atomic_caches.values()):
            logger.warning(
                "Cachalot atomic_caches contains uncommitted values "
                "(probably a bug in cachalot), clearing atomic_cache and invalidating"
            )
            atomic_caches.clear()  # Clear values so they don't persist in the next request
            # Invalidate everything to ensure there are no stale versions
            # of the uncommitted values in the cache
            invalidate(db_alias="default")

        return response
