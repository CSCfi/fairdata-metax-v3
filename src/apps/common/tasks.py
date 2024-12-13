import logging

from django.conf import settings
from django_q.tasks import async_task

logger = logging.getLogger()


def run_task(fn, *args, **kwargs):
    """Run function as a background task.

    Because tasks use the default DB connection, they aren't actually
    created in the DB until the current transaction is committed succesfully.
    This is usually what we want because task workers cannot access
    data that has not been committed yet.
    """
    if settings.ENABLE_BACKGROUND_TASKS:
        task_id = async_task(fn, *args, **kwargs)
        logger.info(f"Scheduled async task '{fn.__name__}' with task_id={task_id}")
    else:
        # Background tasks disabled, run immediately
        fn(*args, **kwargs)
