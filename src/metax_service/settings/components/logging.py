import logging
import os
import time
from urllib.parse import urlparse

from environs import Env

from apps.common.context import ctx_request

env = Env()


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.


class LogFormatter(logging.Formatter):
    """Custom log formatter.

    Includes:
    - Timestamp as datetime with milliseconds and Z timezone.
    - Additional 'source' attribute for determining what made the request.
    """

    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03dZ"
    converter = time.gmtime

    def get_special_user(self, request) -> str:
        if user := getattr(request, "user", None):
            is_service = any(g.name == "service" for g in user.groups.all())
            if is_service or user.is_staff or user.is_superuser:
                return request.user.username
        return ""

    def get_request_origin_host(self, request) -> str:
        """Return host from request origin headers."""
        try:
            origin = request.headers.get("origin", "")
            return urlparse(origin).netloc
        except Exception:
            return ""

    def get_source(self) -> str:
        """Return source of request.

        For special users (service, staff, admin) return username.
        For cross-origin requests, return host.
        """
        if request := ctx_request.get():
            if special_user := self.get_special_user(request):
                return special_user
            elif origin := self.get_request_origin_host(request):
                return origin
        return "-"

    def format(self, record):
        record.source = self.get_source()
        return super().format(record)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "class": "metax_service.settings.components.logging.LogFormatter",
            "format": "%(asctime)s p%(process)d %(source)s %(name)s %(levelname)s: %(message)s",
        },
        "simple": {
            "class": "metax_service.settings.components.logging.LogFormatter",
            "format": "{levelname} {source} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.NullHandler",  # Disabled by default
        },
        "queries_file": {
            "class": "logging.NullHandler",  # Disabled by default
        },
    },
    "loggers": {
        "apps.common.profiling.queries": {
            # Propagate to root unless LOG_QUERIES_FILE is set
            "propagate": True,
            "handlers": [],
        }
    },
    "root": {
        "level": os.environ.get("DJANGO_LOG_LEVEL", default="INFO"),
        "handlers": ["console", "file"],
    },
}


# Log SQL queries?
LOG_QUERIES = env.bool("LOG_QUERIES", False)
# Set to log queries in a separate file. If not set, the default file logger is used.
LOG_QUERIES_FILE = env.str("LOG_QUERIES_FILE", "")
# Minimum duration in seconds for query to be logged
SLOW_QUERY_LIMIT = env.float("SLOW_QUERY_LIMIT", 0)
# If queries by request exceed total limit or a query was slow, log total queries for request
SLOW_TOTAL_QUERIES_LIMIT = env.float("SLOW_TOTAL_QUERIES_LIMIT", 0)

LOG_FILE = os.environ.get("DJANGO_ERROR_LOG_FILENAME")
if LOG_FILE:
    LOGGING["handlers"]["file"] = {
        "level": "INFO",
        "class": "logging.FileHandler",
        "filename": LOG_FILE,
        "formatter": "verbose",
    }

if LOG_QUERIES_FILE:
    LOGGING["handlers"]["queries_file"] = {
        "level": "INFO",
        "class": "logging.FileHandler",
        "filename": LOG_QUERIES_FILE,
        "formatter": "verbose",
    }
    LOGGING["loggers"]["apps.common.profiling.queries"] = {
        "handlers": ["queries_file"],
        "propagate": False,
    }
