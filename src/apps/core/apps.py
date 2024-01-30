from django.apps import AppConfig
from watson import search


class DatasetSearchAdapter(search.SearchAdapter):
    def get_title(self, obj):
        if not obj.catalogrecord_ptr_id:
            return [] # prevent trying to index deleted draft

        criteria = []
        criteria.append(str(obj.persistent_identifier))
        criteria.append(obj.title)
        criteria.append([actor.person.name for actor in obj.actors.all() if actor.person])
        criteria.append(
            [
                actor.person.external_identifier
                for actor in obj.actors.all()
                if actor.person and actor.person.external_identifier
            ]
        )
        criteria.append(obj.theme.all())
        return criteria

    def get_description(self, obj):
        if not obj.catalogrecord_ptr_id:
            return [] # prevent trying to index deleted draft

        criteria = []
        criteria.append(obj.description)
        criteria.append(obj.keyword)
        return criteria

    def get_content(self, obj):
        if not obj.catalogrecord_ptr_id:
            return [] # prevent trying to index deleted draft

        criteria = []
        criteria.append(obj.relation.all())
        criteria.append(obj.other_identifiers.all())
        return criteria


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from apps.core import signals

        dataset = self.get_model("Dataset")
        search.register(dataset, DatasetSearchAdapter)
