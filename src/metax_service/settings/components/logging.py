import logging
import time
import os

from environs import Env

env = Env()


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
class DateTimeZFormatter(logging.Formatter):
    """Log formatter with datetime with milliseconds and Z timezone."""

    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03dZ"
    converter = time.gmtime


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "class": "metax_service.settings.components.logging.DateTimeZFormatter",
            "format": "%(asctime)s p%(process)d %(name)s %(levelname)s: %(message)s",
        },
        "simple": {
            "class": "metax_service.settings.components.logging.DateTimeZFormatter",
            "format": "{levelname} {asctime} {module} {message}",
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
