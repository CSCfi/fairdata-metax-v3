from metax_service.settings.components.base import DATABASES

DATABASES["default"]["CONN_MAX_AGE"] = 30
DATABASES["default"]["ATOMIC_REQUESTS"] = True

DEBUG = True

PID_MS_CLIENT_INSTANCE = "apps.core.services.pid_ms_client._PIDMSClient"