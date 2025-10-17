import logging
from collections import Counter
from contextlib import ContextDecorator, contextmanager
from datetime import datetime
from inspect import currentframe, getframeinfo
from os import path
import re

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


# Match SQL query strings where placeholder "%s, " is repeated a lot
re_repeated_s = re.compile(r"(?:%s, ){9,}")


class log_queries(ContextDecorator):
    """Context manager and decorator to log Django SQL queries.

    Uses Django database instrumentation wrapper installed
    on a thread-local connection object.

    Args:
        slow_limit (float): Minimum execution time (in seconds) for a query to be logged.
                            Queries faster than this threshold will not be logged.
        show_params (bool): Whether to include query parameters in the log output.
                            If True, parameters are shown (truncated if long); otherwise, omitted.
        log_total (bool):   If True, log total SQL query count and duration.
        connection:         Django connection object.
        label (str):        Extra label to use when logging.

    Usage as context manager:
        with log_queries(slow_limit=0.5):
            # Django ORM queries here

    Usage as decorator:
        @log_queries(slow_limit=0.5)
        def run_queries():
            # Django ORM queries here
    """

    def __init__(
        self,
        slow_limit: float = 0,
        show_params=True,
        log_total=True,
        connection=connection,
        label="",
    ):
        self.slow_limit = slow_limit
        self.show_params = show_params
        self.connection = connection
        self.label = label
        self.log_total = log_total
        self.total_count = 0
        self.total_elapsed = 0

    def format_params(self, params: str) -> str:
        if not self.show_params:
            return ""
        s = str(params)
        if len(s) > 200:
            s = f"{s[:150]} ... {s[-50:]}"
        return f", params={s}"

    def format_query(self, query: str) -> str:
        """Truncate repeated %s in queries to make e.g. "... WHERE id IN (%s, %s, ...)" more readable."""
        return re_repeated_s.sub("%s, %s, %s, %s, ..., %s, ", str(query))

    def format_label(self):
        return f"{self.label} --- " if self.label else ""

    def __enter__(self):
        def exec(execute, sql, params, many, context):
            label = self.format_label()
            start = datetime.now()
            try:
                execute(sql, params, many, context)
            except Exception as error:
                elapsed = (datetime.now() - start).total_seconds()
                errorname = error.__class__.__name__
                logger.error(f"{label}{errorname} during query ({elapsed:.3f}s): {sql})")
                raise
            elapsed = (datetime.now() - start).total_seconds()
            self.total_count += 1
            self.total_elapsed += elapsed
            if elapsed >= self.slow_limit:
                many_str = "many " if many else ""
                logger.info(
                    f"{label}Execute SQL {many_str}({elapsed:.3f}s): "
                    f"{self.format_query(sql)}{self.format_params(params)}"
                )

        self.wrapper = self.connection.execute_wrapper(exec)
        self.wrapper.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.log_total:
            label = self.format_label()
            logger.info(
                f"{label}Total SQL queries: {self.total_count} ({self.total_elapsed:.3f}s)"
            )
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
