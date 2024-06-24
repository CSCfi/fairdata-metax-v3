import logging
from collections import Counter
from contextlib import contextmanager
from inspect import currentframe, getframeinfo
from os import path

from django.db.models.sql.compiler import SQLCompiler, SQLInsertCompiler, SQLUpdateCompiler

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
