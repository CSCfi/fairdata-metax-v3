import uuid
from enum import Enum

from django.db import connection


class LockType(Enum):
    sync_dataset = 1


def advisory_lock(type: LockType, key: int):
    """Acquire advisory lock that is released at end of transaction.

    The function blocks until a lock is acquired.

    Advisory locks do not prevent database modifications by themselves
    and need to be enforced on the application level.
    """

    # Two 32-bit integer values are required to identify the locked resource.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", (type.value, key))


def lock_id(type: LockType, id: uuid.UUID):
    """Helper to acquire advisory lock for a UUID."""
    # Use last 4 bytes to get a 32-bit signed int
    key = int.from_bytes(id.bytes[-4:], "big", signed=True)
    advisory_lock(type=type, key=key)


def lock_sync_dataset(id: uuid.UUID):
    """Acquire lock for dataset syncing until end of transaction."""
    lock_id(type=LockType.sync_dataset, id=id)
