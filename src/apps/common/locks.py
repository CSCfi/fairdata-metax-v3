import uuid
from enum import Enum

from django.db import connection


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
