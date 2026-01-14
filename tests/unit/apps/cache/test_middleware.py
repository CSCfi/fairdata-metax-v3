import logging

import pytest
from cachalot.cache import cachalot_caches
from django.test import RequestFactory

from apps.cache.middleware import CachalotClearMiddleware


def noop(request):
    """Do nothing"""


def fake_cache_data(request):
    """Add fake uncomitted data to cachalot atomic_caches."""
    caches = cachalot_caches.atomic_caches
    caches["default"].append({"some": "data"})


@pytest.fixture
def clear_atomic_caches():
    """Clear atomic_caches after test to ensure we don't cause side effect in other tests."""
    yield
    cachalot_caches.atomic_caches.clear()


# Clearing atomic_caches should not be done in a transaction,
# make test transactional so it won't be automatically run in a transaction
@pytest.mark.django_db(transaction=True)
def test_cachalot_clear_middleware(caplog, clear_atomic_caches):
    """Ensure uncommitted data in cachalot atomic cache is cleared at end of a request."""
    logging.disable(logging.NOTSET)
    request = RequestFactory()

    caches = cachalot_caches.atomic_caches
    assert caches["default"] == []

    # Cachalot atomic_caches has no data, middleware should do nothing
    middleware = CachalotClearMiddleware(get_response=noop)
    middleware(request.get("/"))
    assert len(caplog.messages) == 0

    # Cachalot atomic_caches has uncommitted data from the request (which should not happen),
    # middleware should clear the cache and log a warning
    middleware = CachalotClearMiddleware(get_response=fake_cache_data)
    middleware(request.get("/"))
    assert caches["default"] == []
    assert len(caplog.messages) == 1
    assert "atomic_caches contains uncommitted values" in caplog.messages[0]
