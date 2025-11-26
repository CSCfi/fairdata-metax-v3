import logging
from collections import Counter
from contextlib import ContextDecorator, contextmanager
from datetime import datetime
from inspect import currentframe, getframeinfo
from os import path
import traceback
import re

from django.conf import settings
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


queries_logger = logging.getLogger(f"{__name__}.queries")

# Match SQL query strings where placeholder "%s, " is repeated a lot
re_repeated_s = re.compile(r"(?:%s, ){9,}")

# Match SQL query strings where "(%s, %s, %s, ..., %s), " is repeated
re_values = r"\((?:%s, )+%s\)"
re_repeated_values = re.compile(rf"({re_values}, )(?:{re_values}, )(?:{re_values}, )+")

# Match SQL query strings with CASE WHEN ... THEN ... WHEN ... THEN ... END
re_when = r"WHEN \([^)]+\) THEN .+?"
re_case = re.compile(rf"CASE ({re_when})(?:{re_when})+(ELSE\s+.+?)? END")


class log_queries(ContextDecorator):
    """Context manager and decorator to log Django SQL queries.

    Uses Django database instrumentation wrapper installed
    on a thread-local connection object.

    Args:
        slow_limit (float): Minimum execution time (in seconds) for a query to be logged.
                            Queries faster than this threshold will not be logged.
        slow_total_limit (float): Log query totals if total limit is exceeded or
                            at least one query was logged, and log_total is enabled.
        show_params (bool): Whether to include query parameters in the log output.
                            If True, parameters are shown (truncated if long); otherwise, omitted.
        log_total (bool):   If True, allow logging total SQL query count and duration.
        analyze (bool):     Analyze logged SELECT queries. Analyzed queries are executed twice.
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
        slow_total_limit: float = 0,
        show_params=True,
        log_total=True,
        analyze=False,
        connection=connection,
        label="",
    ):
        self.slow_limit = slow_limit
        self.slow_total_limit = slow_total_limit
        self.show_params = show_params
        self.connection = connection
        self.label = label
        self.log_total = log_total
        self.analyze = analyze
        self.total_count = 0
        self.total_elapsed = 0
        self.logged = False  # show total if some queries were logged

    def query_has_sensitive_values(self, sql: str) -> bool:
        """Omit SQL params if they might contain credentials."""
        if "session_key" in sql:
            return True
        if "password" in sql:
            return True
        if "knox_authtoken" in sql:
            return True
        return False

    def format_params(self, sql: str, params) -> str:
        if not self.show_params:
            return ""
        if self.query_has_sensitive_values(sql):
            params = "******"
        s = str(params)
        if len(s) > 200:
            s = f"{s[:150]} ... {s[-50:]}"
        return f"; params={s}"

    def format_query(self, query: str) -> str:
        """Truncate repeated %s in queries to make
        e.g. "... WHERE id IN (%s, %s, ...)" more readable.
        """
        query = re_case.sub(r"CASE \g<1>...\g<2> END", query)
        query = re_repeated_values.sub(r"\g<1>..., ", query)
        query = re_repeated_s.sub("%s, %s, %s, %s, ..., %s, ", query)
        if len(query) > 2000:
            query = f"{query[:1800]} ... {query[-200:]}"
        return query

    def format_label(self):
        return f"{self.label} --- " if self.label else ""

    def get_user_code_line(self) -> str:
        """Get Metax line that triggered the query."""
        project_root = path.abspath(settings.BASE_DIR)
        stack = traceback.extract_stack()

        # Find closest stack frame that is in the Metax project and is not in profiling.py
        for frame in reversed(stack):
            filename = frame.filename
            is_user_code = (
                path.abspath(filename).startswith(project_root)
                and path.basename(filename) != "profiling.py"
            )
            if is_user_code:
                rel_path = path.relpath(frame.filename, start=project_root)
                return f" [{rel_path}:{frame.lineno} in {frame.name}]"
        return ""

    def analyze_query(self, sql: str, params: list, many: bool, context: dict):
        if not sql.startswith("SELECT "):
            return  # Don't analyze updates to avoid duplicating query effects
        if self.query_has_sensitive_values(sql):
            return  # Avoid possibly exposing credentials in the query plan
        connection = context["connection"]
        with connection.cursor() as c:
            label = self.format_label()
            sql = f"EXPLAIN ANALYZE {sql}"

            # Using normal c.execute or c.executemany would retrigger our `exec`
            # so use the underscored versions to avoid an infinite loop.
            if many:
                c._executemany(sql, params)
            else:
                c._execute(sql, params)

            analysis = "\n".join(row[0][:200] for row in c.fetchall())
            queries_logger.info(f"{label}EXPLAIN ANALYZE:\n{analysis}")

    def __enter__(self):
        def exec(execute, sql: str, params: list, many: bool, context: dict):
            label = self.format_label()
            start = datetime.now()
            try:
                execute(sql, params, many, context)
            except Exception as error:
                elapsed = (datetime.now() - start).total_seconds()
                errorname = error.__class__.__name__
                self.logged = True
                queries_logger.error(f"{label}{errorname} during query ({elapsed:.3f}s): {sql})")
                raise
            elapsed = (datetime.now() - start).total_seconds()
            self.total_count += 1
            self.total_elapsed += elapsed
            if elapsed >= self.slow_limit:
                many_str = "many " if many else ""
                self.logged = True
                code_line = self.get_user_code_line()
                queries_logger.info(
                    f"{label}Execute SQL {many_str}({elapsed:.3f}s){code_line}: "
                    f"{self.format_query(sql)}{self.format_params(sql, params)}"
                )
                if self.analyze:
                    self.analyze_query(sql, params, many, context)

        self.wrapper = self.connection.execute_wrapper(exec)
        self.wrapper.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.log_total and (self.logged or (self.total_elapsed > self.slow_total_limit)):
            label = self.format_label()
            queries_logger.info(
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
