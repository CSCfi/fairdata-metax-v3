import pytest
from django.core.cache.backends.memcached import PyMemcacheCache
from pymemcache.exceptions import MemcacheServerError

from apps.cache.caches import IgnoreTooLargePyMemcacheCache


def fail_too_large(*args, **kwargs):
    raise MemcacheServerError(b"object too large for cache")


def fail_other_error(*args, **kwargs):
    raise MemcacheServerError(b"some random error")


def test_cache_set(monkeypatch):
    cache = IgnoreTooLargePyMemcacheCache("notarealserver", {})

    monkeypatch.setattr(PyMemcacheCache, "set", lambda *args, **kwargs: None)
    cache.set("key", "value")

    monkeypatch.setattr(PyMemcacheCache, "set", fail_too_large)
    cache.set("key", "value")

    with pytest.raises(MemcacheServerError):
        monkeypatch.setattr(PyMemcacheCache, "set", fail_other_error)
        cache.set("key", "value")


def test_cache_set_many(monkeypatch):
    cache = IgnoreTooLargePyMemcacheCache("notarealserver", {})

    monkeypatch.setattr(PyMemcacheCache, "set_many", lambda *args, **kwargs: [])
    cache.set_many({"key": "value"})

    monkeypatch.setattr(PyMemcacheCache, "set_many", fail_too_large)
    cache.set_many({"key": "value"})

    with pytest.raises(MemcacheServerError):
        monkeypatch.setattr(PyMemcacheCache, "set_many", fail_other_error)
        cache.set_many({"key": "value"})
