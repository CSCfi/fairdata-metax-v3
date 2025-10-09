import logging
from contextlib import contextmanager
from typing import Optional
import uuid
from enum import Enum

from django.db import connection, transaction, utils, models
import psycopg.errors
from rest_framework import exceptions

from apps.common.exceptions import ResourceLocked


logger = logging.getLogger(__name__)


class LockType(Enum):
    sync_dataset = 1
    rems_publish = 2


def advisory_lock(type: LockType, key: int, block=True) -> bool:
    """Acquire advisory lock that is released at end of transaction.

    If block=True (default), the function blocks until a lock is acquired.

    Advisory locks do not prevent database modifications by themselves
    and need to be enforced on the application level.
    """

    # Two 32-bit integer values are required to identify the locked resource.
    with connection.cursor() as cursor:
        if block:
            # Block until lock is free
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", (type.value, key))
            return True

        # Return True if lock was acquired, False otherwise
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s, %s)", (type.value, key))
        return bool(cursor.fetchone()[0])


def get_key_from_uuid(id: uuid.UUID) -> int:
    """Helper to convert a UUID into a 32-bit key usable in advisory_lock."""
    # Use last 4 bytes to get a 32-bit signed int
    return int.from_bytes(id.bytes[-4:], "big", signed=True)


def lock_sync_dataset(id: uuid.UUID, block=True):
    """Acquire lock for dataset syncing until end of transaction."""
    key = get_key_from_uuid(id)
    return advisory_lock(type=LockType.sync_dataset, key=key, block=block)


def lock_rems_publish(id: uuid.UUID, block=True):
    """Acquire lock for dataset syncing to REMS until end of transaction."""
    key = get_key_from_uuid(id)
    return advisory_lock(type=LockType.rems_publish, key=key, block=block)


@contextmanager
def lock_timeout(timeout: float = 0):
    """Set lock timeout for the duration of the context manager.

    Parameters:
        timeout (float): Timeout in seconds. If 0, lock timeout is not altered.
    """

    with connection.cursor() as cursor:
        previous_timeout = None
        if timeout:
            cursor.execute("SHOW lock_timeout")  # Get previous value so we can later restore it
            previous_timeout = cursor.fetchone()[0]

            # Use SET LOCAL so the value is always reverted at end of transaction
            cursor.execute("SET LOCAL lock_timeout = %s", [f"{timeout:f}s"])
        try:
            yield
        finally:
            if previous_timeout is not None:
                try:
                    # Attempt to revert timeout to previous value
                    cursor.execute("SET LOCAL lock_timeout = %s", [previous_timeout])
                except utils.InternalError:
                    pass  # We can safely ignore reverting timeout failed due to e.g. aborted transaction


def get_lock_timeout():
    """Get lock timeout value."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW lock_timeout")
        return cursor.fetchone()[0]


def select_queryset_for_update(queryset: models.QuerySet, timeout: float = 0) -> models.QuerySet:
    """Lock queryset for update.

    This function attempts to acquire a row-level lock on the records returned by the queryset.
    Rows in related models are not locked. The queryset is evaluated to acquire the lock.

    Parameters:
        queryset (QuerySet): The Django queryset to lock.
        timeout (float): Optional timeout in seconds for acquiring the lock.
            If 0, raises LockNotAvailable immediately instead of blocking.

    Returns:
        QuerySet: The same queryset with row-level locking applied
    """

    with lock_timeout(timeout):
        try:
            # Use of=("self",) to ensure related objects are not locked
            queryset = queryset.select_for_update(of=("self",), nowait=not timeout, no_key=True)
            len(queryset)  # Force queryset evaluation so the lock is acquired here
        except utils.OperationalError as exc:
            if isinstance(exc.__cause__, psycopg.errors.LockNotAvailable):
                logger.warning(f"Could not acquire lock for {queryset.model.__name__}. {timeout=}")
                raise ResourceLocked(
                    detail=f"Could not acquire lock for {queryset.model.__name__}."
                )
            raise
    return queryset
