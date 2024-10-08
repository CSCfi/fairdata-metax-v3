"""
Django settings for metax_service project.

Generated by 'django-admin startproject' using Django 3.2.12.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import json
import os
import sys
from datetime import timedelta
from os.path import join
from pathlib import Path

import factory.random
from django.utils.translation import gettext_lazy as _
from environs import Env

env = Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = Path(__file__).resolve().parent.parent

ROOT_DIR = BASE_DIR.parent

APPS_DIR = join(BASE_DIR, "apps")

sys.path.append(APPS_DIR)

# collect static files here
STATIC_ROOT = os.environ.get("STATIC_ROOT", join(ROOT_DIR, "staticfiles"))
STATIC_URL = "/v3/static/"

NO_NGINX_PROXY = os.environ.get("NO_NGINX_PROXY", True)

# collect media files here
MEDIA_ROOT = join(ROOT_DIR, "media")

# watchman storage setting
WATCHMAN_STORAGE_PATH = "django-watchman/"

# look for static assets here
STATICFILES_DIRS = [
    join(ROOT_DIR, "static"),
]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-+#ohm#9qx8+2gc28g6%r8iww^8f&yye_)^-&=3x51kzw$&svk("
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False)

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,0.0.0.0,127.0.0.1,[::1]").split(", ")
INTERNAL_IPS = os.environ.get("INTERNAL_IPS", "127.0.0.1").split(",")

# Application definition

DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "knox",
    "django_extensions",
    "drf_yasg",
    "django_filters",
    "simple_history",
    "watchman",
    "polymorphic",
    "corsheaders",
    "watson",
    "cachalot",
    "hijack",
    "hijack.contrib.admin",
    "django_json_widget",
]
LOCAL_APPS = [
    "common.apps.CommonConfig",
    "users.apps.UsersConfig",
    "core.apps.CoreConfig",
    "refdata.apps.ReferenceDataConfig",
    "actors.apps.ActorsConfig",
    "files.apps.FilesConfig",
    "router.apps.RouterConfig",
    "cache.apps.CacheConfig",
    "download.apps.DownloadConfig",
]

INSTALLED_APPS = LOCAL_APPS + DEFAULT_APPS + THIRD_PARTY_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.users.middleware.SameOriginCookiesMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "watson.middleware.SearchContextMiddleware",
    "hijack.middleware.HijackUserMiddleware",
]

ROOT_URLCONF = "metax_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(ROOT_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "metax_service.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DATABASE_NAME"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASS"),
        "HOST": os.getenv("POSTGRES_HOST", default="localhost"),
        "PORT": os.getenv("POSTGRES_PORT", default="5432"),
    }
}
# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {"level": os.environ.get("DJANGO_LOG_LEVEL", default="INFO"), "handlers": ["console"]},
}


LANGUAGE_CODE = "en-us"
LANGUAGES = (("en-us", _("English")), ("fi", _("Finnish")))
LOCALE_PATHS = (os.path.join(APPS_DIR, "core/locale"),)
TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.MetaxUser"

# permissions
# https://www.django-rest-framework.org/api-guide/authentication/#setting-the-authentication-scheme
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.SSOAuthentication",
        "apps.users.authentication.SSOSyncBasicAuthentication",
        "apps.users.authentication.SSOSyncSessionAuthentication",
        "apps.users.authentication.SSOSyncKnoxTokenAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultOffsetPagination",
    "DEFAULT_FILTER_BACKENDS": ("apps.common.filters.CustomDjangoFilterBackend",),
    "EXCEPTION_HANDLER": "common.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "apps.common.renderers.MsgspecJSONRenderer",
        "apps.common.renderers.NoHTMLFormBrowsableAPIRenderer",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
}
ENABLE_DRF_TOKEN_AUTH = env.bool("ENABLE_DRF_TOKEN_AUTH", False)
if ENABLE_DRF_TOKEN_AUTH:
    INSTALLED_APPS = INSTALLED_APPS + ["rest_framework.authtoken"]
    AUTH_CLASSES = REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = AUTH_CLASSES + [
        "rest_framework.authentication.TokenAuthentication"
    ]

# Importing these also imports django.conf.settings which triggers
# some deprecation checks while settings have not been fully loaded.
# Import late in file to avoid e.g. warnings about changed default
# in USE_TZ.
from drf_yasg.app_settings import SWAGGER_DEFAULTS

SWAGGER_SETTINGS = {
    "DEEP_LINKING": True,  # Automatically update URL fragment with current operation in Swagger UI
    "DEFAULT_FIELD_INSPECTORS": [
        "apps.common.inspectors.SwaggerDescriptionInspector",
        "apps.common.inspectors.URLReferencedModelFieldInspector",
        *SWAGGER_DEFAULTS["DEFAULT_FIELD_INSPECTORS"],
    ],
    "DEFAULT_AUTO_SCHEMA_CLASS": "apps.common.inspectors.ExtendedSwaggerAutoSchema",
    "DEFAULT_GENERATOR_CLASS": "apps.common.generators.SortingOpenAPISchemaGenerator",
    "DEFAULT_INFO": "metax_service.urls.openapi_info",
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
    "VALIDATOR_URL": None,
}
REDOC_SETTINGS = {"HIDE_HOSTNAME": True}

FACTORY_BOY_RANDOM_SEED = "metax-service"

factory.random.reseed_random(FACTORY_BOY_RANDOM_SEED)


# Allow access to dataset file metadata models and serializers
# without depending explicitly on the core app
DATASET_FILE_METADATA_MODELS = {
    "file": "apps.core.models.file_metadata.FileSetFileMetadata",
    "directory": "apps.core.models.file_metadata.FileSetDirectoryMetadata",
}
DATASET_FILE_METADATA_SERIALIZERS = {
    "file": "apps.core.serializers.file_metadata_serializer.FileMetadataSerializer",
    "directory": "apps.core.serializers.file_metadata_serializer.DirectoryMetadataSerializer",
}

LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE = {
    "urn:nbn:fi:att:file-storage-ida": "ida",
    "urn:nbn:fi:att:file-storage-pas": "pas",
    "pid:urn:storageidentifier1": "legacy-test-storage-1",
}
V3_STORAGE_SERVICE_TO_LEGACY_FILE_STORAGE = {
    value: key for key, value in LEGACY_FILE_STORAGE_TO_V3_STORAGE_SERVICE.items()
}

# Define supported storage services and their FileStorage proxy class
STORAGE_SERVICE_FILE_STORAGES = {
    "test": "BasicFileStorage",
    "ida": "IDAFileStorage",
    "pas": "ProjectFileStorage",
    "legacy-test-storage-1": "ProjectFileStorage",
}

# User groups that can see all projects in storage service
PROJECT_STORAGE_SERVICE_USER_GROUPS = {"ida", "pas"}


# Profiling
ENABLE_DEBUG_TOOLBAR = env.bool("ENABLE_DEBUG_TOOLBAR", True)
ENABLE_SILK_PROFILER = env.bool("ENABLE_SILK_PROFILER", False)

# Languages

DISPLAY_API_LANGUAGES = ["en", "fi", "sv"]


# SSO Auth

ENABLE_SSO_AUTH = env.bool("ENABLE_SSO_AUTH", False)
SSO_HOST = env.str("SSO_HOST", None)
SSO_SESSION_COOKIE = env.str("SSO_SESSION_COOKIE", None)
SSO_SECRET_KEY = env.str("SSO_SECRET_KEY", None)
SSO_METAX_SERVICE_NAME = env.str("SSO_METAX_SERVICE_NAME", None)

# Token required by SSO /user_status and /project_status endpoints
SSO_TRUSTED_SERVICE_TOKEN = env.str("SSO_TRUSTED_SERVICE_TOKEN", None)

# CSRF configuration
# Note: CSRF_TRUSTED_ORIGINS require a scheme (e.g. https://someurl.com) in Django 4.0
# but older versions expect scheme not to be present (e.g. someurl.com).
CSRF_TRUSTED_ORIGINS = [
    (
        origin
        if (origin.startswith("http://") or origin.startswith("https://"))
        else f"https://{origin}"
    )
    for origin in env.list("CSRF_TRUSTED_ORIGINS", [])
]

# CORS header settings for django-cors-headers
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", [])
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", False)

REST_KNOX = {
    "AUTH_HEADER_PREFIX": "Bearer",
    "TOKEN_TTL": timedelta(weeks=8),
    "TOKEN_LIMIT_PER_USER": 5,
}

# Enable view that allows listing and deleting users (and user data) for testing purposes
ENABLE_USERS_VIEW = env.bool("ENABLE_USERS_VIEW", False)

# PID Microservice
PID_MS_CLIENT_INSTANCE = env.str(
    "PID_MS_CLIENT_INSTANCE", "apps.core.services.pid_ms_client._DummyPIDMSClient"
)
PID_MS_BASEURL = env.str("PID_MS_BASEURL", None)
PID_MS_APIKEY = env.str("PID_MS_APIKEY", None)
ETSIN_URL = env.str("ETSIN_URL", None)

# Common global query parameters shared by most endpoints but not documented in swagger
COMMON_QUERY_PARAMS = {
    "format",  # DRF output format,  e.g.  ?format=json or ?format=api
    "strict",  # set ?strict=false to allow unknown query params without throwing error
    "include_nulls",  # set ?include_nulls=true include null values in responses
}

# Email configuration
EMAIL_HOST = env.str("EMAIL_HOST", None)
EMAIL_PORT = env.str("EMAIL_PORT", None)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", None)
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", None)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", False)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
METAX_EMAIL_SENDER = env.str("METAX_EMAIL_SENDER", "noreply@fairdata.fi")

# Syncing datasets to Metax V2
METAX_V2_INTEGRATION_ENABLED = env.bool("METAX_V2_INTEGRATION_ENABLED", False)
METAX_V2_HOST = env.str("METAX_V2_HOST", None)
METAX_V2_USER = env.str("METAX_V2_USER", None)
METAX_V2_PASSWORD = env.str("METAX_V2_PASSWORD", None)

# Ensure redirect v1/v2 -> v3
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Metrics
METRICS_REPORT_URL = env.str("METRICS_REPORT_URL", None)
