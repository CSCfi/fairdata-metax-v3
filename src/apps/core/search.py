from django.db.models import Prefetch, prefetch_related_objects
from watson import search

from apps.core.models import Dataset, DatasetActor


class DatasetSearchAdapter(search.SearchAdapter):
    # Title field is limited to 1000 characters
    max_title_length = 1000

    def _get_refdata_values(self, field):
        values = set()
        for entry in field.all():
            for value in entry.pref_label.values():
                values.add(value)
        return sorted(values)

    def _collect_organizations(self, actor: DatasetActor, organizations: set):
        organization = actor.organization
        while organization:
            organizations.add(organization.pref_label.get("fi"))
            organizations.add(organization.pref_label.get("en"))
            organizations.add(organization.pref_label.get("sv"))
            organizations.add(organization.pref_label.get("und"))
            organization = organization.parent

    def _get_actors(self, obj: Dataset):
        criteria = []
        criteria.extend([actor.person.name for actor in obj.actors.all() if actor.person])
        criteria.extend(
            [
                actor.person.external_identifier
                for actor in obj.actors.all()
                if actor.person and actor.person.external_identifier
            ]
        )
        organizations = set()
        for actor in obj.actors.all():
            self._collect_organizations(actor, organizations)
        if None in organizations:
            organizations.remove(None)

        criteria.extend(sorted(organizations))
        return criteria

    def get_title(self, obj: Dataset):
        criteria = []
        criteria.append(str(obj.persistent_identifier))
        criteria.extend(obj.title.values())
        criteria.extend(self._get_refdata_values(obj.theme))
        criteria.extend(self._get_actors(obj))
        return (" ".join(criteria))[: self.max_title_length]

    def get_description(self, obj: Dataset):
        criteria = []
        if obj.description:
            criteria.extend(obj.description.values())
        criteria.extend(obj.keyword)

        # Repeat actors here in case they get cut off from title
        criteria.extend(self._get_actors(obj))
        return " ".join(criteria)

    def get_content(self, obj: Dataset):
        criteria = []
        criteria.extend(
            [
                rel.entity.entity_identifier
                for rel in obj.relation.all()
                if rel.entity.entity_identifier
            ]
        )
        criteria.extend([oi.notation for oi in obj.other_identifiers.all()])
        return " ".join(criteria)
