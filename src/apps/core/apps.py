from django.apps import AppConfig
from watson import search


class DatasetSearchAdapter(search.SearchAdapter):
    # Title field is limited to 1000 characters
    max_title_length = 1000

    def _get_refdata_values(self, field):
        values = []
        for value in field.values_list("pref_label__values", flat=True):
            values.extend(value)
        return values

    def _get_actors(self, obj):
        criteria = []
        criteria.extend([actor.person.name for actor in obj.actors.all() if actor.person])
        criteria.extend(
            [
                actor.person.external_identifier
                for actor in obj.actors.all()
                if actor.person and actor.person.external_identifier
            ]
        )
        return criteria

    def get_title(self, obj):
        if not obj.catalogrecord_ptr_id:
            return []  # prevent trying to index deleted draft

        criteria = []
        criteria.append(str(obj.persistent_identifier))
        criteria.extend(obj.title.values())
        criteria.extend(self._get_refdata_values(obj.theme))
        criteria.extend(self._get_actors(obj))
        return (" ".join(criteria))[: self.max_title_length]

    def get_description(self, obj):
        if not obj.catalogrecord_ptr_id:
            return []  # prevent trying to index deleted draft

        criteria = []
        if obj.description:
            criteria.extend(obj.description.values())
        criteria.extend(obj.keyword)

        # Repeat actors here in case they get cut off from title
        criteria.extend(self._get_actors(obj))
        return " ".join(criteria)

    def get_content(self, obj):
        if not obj.catalogrecord_ptr_id:
            return []  # prevent trying to index deleted draft

        criteria = []
        criteria.extend(
            obj.relation.filter(entity__entity_identifier__isnull=False).values_list(
                "entity__entity_identifier", flat=True
            )
        )
        criteria.extend(obj.other_identifiers.values_list("notation", flat=True))
        return " ".join(criteria)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from apps.core import signals

        dataset = self.get_model("Dataset")
        search.register(dataset, DatasetSearchAdapter)
