import logging

from django.core.cache.backends.memcached import DEFAULT_TIMEOUT, PyMemcacheCache
from pymemcache.exceptions import MemcacheServerError

logger = logging.getLogger(__name__)


class IgnoreTooLargePyMemcacheCache(PyMemcacheCache):
    """Memcached backend that ignores "object too large" errors.

    Normally Memcached raises an error when caching items
    larger than the cache size limit. This logs those errors
    but won't cause an internal server error.

    Another option would be to drop large items without sending
    them to Memcached at all, but Memcache doesn't tell what the
    limit is and we don't know the item size before serialization,
    so that way would need more configuration and some changes
    in serialization logic.
    """

    def _handle_error(self, error):
        if error.args == (b"object too large for cache",):
            logger.warn(error)
        else:
            raise error

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().set(key, value, timeout=timeout, version=version)
        except MemcacheServerError as error:
            self._handle_error(error)
            return None

    def set_many(self, data: dict, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().set_many(data, timeout=timeout, version=version)
        except MemcacheServerError as error:
            self._handle_error(error)
            return []
