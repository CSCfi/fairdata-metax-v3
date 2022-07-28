from django.apps import AppConfig


class ReferenceDataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.refdata"
    verbose_name = "reference data"
