from django.apps import AppConfig
from watson import search



class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from apps.core import signals
        from apps.core.search import DatasetSearchAdapter

        dataset = self.get_model("Dataset")
        search.register(dataset, DatasetSearchAdapter)
