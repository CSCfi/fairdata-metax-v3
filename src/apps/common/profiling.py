import logging
from collections import Counter
from contextlib import ContextDecorator, contextmanager
from datetime import datetime
from inspect import currentframe, getframeinfo
from os import path

from django.db import connection
from django.db.models.sql.compiler import SQLCompiler, SQLInsertCompiler, SQLUpdateCompiler
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_line():
    frame = currentframe().f_back.f_back.f_back
    frameinfo = getframeinfo(frame)
    return f"{path.relpath(frameinfo.filename)}:{frame.f_lineno}"


@contextmanager
def count_queries(log=False):
    """Context manager for counting SQL queries.

    Queries are grouped by SQLCompiler class and model.
    Set log=True to log the result.

    Usage example:

    >>> with count_queries() as counts:
    >>>    Dataset.objects.prefetch_related("spatial")[:10]
    >>> print(counts)
    {'total': 2, 'SQLCompiler': Counter({'total': 2, 'Dataset': 1, 'Spatial': 1})}
    """
    line = _get_line()
    base_exec = SQLCompiler.execute_sql
    insert_exec = SQLInsertCompiler.execute_sql
    update_exec = SQLUpdateCompiler.execute_sql
    counters = {"total": 0}

    def get_exec(original_func):
        def counting_exec(self, *args, **kwargs):
            name = self.__class__.__name__
            if name not in counters:
                counters[name] = Counter()
            counter = counters[name]
            counters["total"] += 1
            counter.update(["total", self.query.model.__name__])
            res = original_func(self, *args, **kwargs)
            return res

        return counting_exec

    try:
        SQLCompiler.execute_sql = get_exec(original_func=base_exec)
        SQLInsertCompiler.execute_sql = get_exec(original_func=insert_exec)
        SQLUpdateCompiler.execute_sql = get_exec(original_func=update_exec)
        yield counters
    finally:
        SQLCompiler.execute_sql = base_exec
        SQLInsertCompiler.execute_sql = insert_exec
        SQLUpdateCompiler.execute_sql = update_exec
        if log:
            logger.info(f"{line}: {counters}")


class log_queries(ContextDecorator):
    """Context manager and decorator to log Django SQL queries.

    Uses Django database instrumentation wrapper, which is installed
    on a thread-local connection object.

    Args:
        slow_limit (float): Minimum execution time (in seconds) for a query to be logged.
                            Queries faster than this threshold will not be logged.
        show_params (bool): Whether to include query parameters in the log output.
                            If True, parameters are shown (truncated if long); otherwise, omitted.
        connection:         Django connection object.

    Usage as context manager:
        with log_queries(slow_limit=0.5):
            # Django ORM queries here

    Usage as decorator:
        @log_queries(slow_limit=0.5)
        def run_queries():
            # Django ORM queries here
    """

    def __init__(self, slow_limit: float = 0, show_params=True, connection=connection):
        self.slow_limit = slow_limit
        self.show_params = show_params
        self.connection = connection

    def format_params(self, params):
        if not self.show_params:
            return ""
        s = str(params)
        if len(s) > 200:
            s = f"{s[:150]} ... {s[-50:]}"
        return f", params={s}"

    def __enter__(self):
        def exec(execute, sql, params, many, context):
            start = datetime.now()
            execute(sql, params, many, context)
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed >= self.slow_limit:
                many_str = "many " if many else ""
                logger.info(
                    f"Execute SQL {many_str}({elapsed:.3f}s): {sql}{self.format_params(params)}"
                )

        self.wrapper = self.connection.execute_wrapper(exec)
        self.wrapper.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.wrapper.__exit__(exc_type, exc_value, traceback)


@contextmanager
def log_duration(log=False):
    """Log duration of context manager in seconds.

    Usage example:

    >>> with log_duration():
    >>>    time.sleep(1)
    INFO ...: Duration 1.00 s
    """

    line = _get_line()
    times = {"start": timezone.now()}
    yield times
    times["end"] = timezone.now()
    times["duration"] = (times["end"] - times["start"]).total_seconds()
    logger.info(f"{line}: Duration {times['duration']:.2f} s")
