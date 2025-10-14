import logging
from typing import TYPE_CHECKING, Iterable, List, NamedTuple, Set

from django.db import models
from django.utils.translation import gettext as _

from apps.common.helpers import single_translation


if TYPE_CHECKING:
    from apps.core.models.catalog_record.dataset import Dataset

logger = logging.getLogger(__name__)


from django.db.models.functions import Coalesce
from django.db.models import F


def coalesce_translation(field, language):
    """Coalesce first matching translation from multi-language field."""
    return Coalesce(
        f"{field}__{language}",
        f"{field}__en",
        f"{field}__fi",
        f"{field}__sv",
        f"{field}__und",
        f"{field}__values__0",  # First entry in values
    )


class EntryTuple(NamedTuple):
    """Dataset index entry as a hashable tuple."""

    language: str
    key: str
    value: str

    @classmethod
    def from_entries(cls, entries: Iterable["DatasetIndexEntry"]) -> List["EntryTuple"]:
        return [EntryTuple(entry.language, entry.key, entry.value) for entry in entries]


class DatasetIndexEntryManager(models.Manager):

    def _get_access_types(self, dataset: "Dataset", language) -> List[EntryTuple]:
        access_type = dataset.access_rights and dataset.access_rights.access_type
        if access_type:
            if label := single_translation(access_type.pref_label, language):
                return [EntryTuple(language, "access_type", label)]
        return []

    def _get_data_catalogs(self, dataset: "Dataset", language) -> List[EntryTuple]:
        data_catalog = dataset.data_catalog
        if data_catalog:
            if label := single_translation(data_catalog.title, language):
                return [EntryTuple(language, "data_catalog", label)]
        return []

    def _get_actor_organization_names(self, queryset: models.QuerySet, language: str) -> List[str]:
        return (
            queryset.annotate(
                aggregation_label=Coalesce(
                    F("organization__parent__parent__pref_label"),
                    F("organization__parent__pref_label"),
                    F("organization__pref_label"),
                )
            )
            .annotate(value=coalesce_translation("aggregation_label", language))
            .values_list("value", flat=True)
            .order_by()  # Remove ordering to ensure so distinct() works properly
            .distinct()
        )

    def _get_creators(self, dataset: "Dataset", language: str) -> List[EntryTuple]:
        orgs = dataset.actors.filter(roles__icontains="creator", organization__isnull=False)
        org_names = list(self._get_actor_organization_names(orgs, language))

        person_names = list(
            dataset.actors.filter(roles__icontains="creator", person__isnull=False)
            .values_list("person__name", flat=True)
            .order_by()
            .distinct()
        )
        return [EntryTuple(language, "creator", name) for name in org_names + person_names if name]

    def _get_organizations(self, dataset: "Dataset", language: str) -> List[EntryTuple]:
        orgs = dataset.actors.order_by().filter(organization__isnull=False)
        org_names = list(self._get_actor_organization_names(orgs, language))
        return [EntryTuple(language, "organization", name) for name in org_names]

    def _get_keywords(self, dataset: "Dataset", language: str) -> List[EntryTuple]:
        return [EntryTuple(language, "keyword", keyword) for keyword in dataset.keyword]

    def _get_reference_data(
        self, dataset: "Dataset", language: str, attribute: str
    ) -> List[EntryTuple]:
        labels = getattr(dataset, attribute).values_list(
            coalesce_translation("pref_label", language), flat=True
        )
        return [EntryTuple(language, attribute, label) for label in labels if label]

    def _get_file_types(self, dataset: "Dataset", language: str) -> List[EntryTuple]:
        fileset = getattr(dataset, "file_set", None)
        if not fileset:
            return []

        labels = (
            fileset.file_metadata.filter(file_type__isnull=False)
            .values_list(coalesce_translation("file_type__pref_label", language), flat=True)
            .order_by()
            .distinct()
        )
        return [EntryTuple(language, "file_type", label) for label in labels if label]

    def _get_projects(self, dataset: "Dataset", language: str) -> List[EntryTuple]:
        labels = dataset.projects.values_list(coalesce_translation("title", language), flat=True)
        return [EntryTuple(language, "project", label) for label in labels if label]

    def _get_existing_instances(self, entries: Iterable[EntryTuple]) -> List["DatasetIndexEntry"]:
        filters = models.Q()
        for language, key, value in entries:
            filters |= models.Q(language=language, key=key, value=value)
        return list(DatasetIndexEntry.objects.filter(filters))

    def create_from_tuples(self, entries: Iterable[EntryTuple]) -> List["DatasetIndexEntry"]:
        return list(
            self.bulk_create(
                [
                    DatasetIndexEntry(language=language, key=key, value=value)
                    for language, key, value in entries
                ]
            )
        )

    def create_for_dataset(self, dataset: "Dataset") -> List["DatasetIndexEntry"]:
        """Get or create index entries for dataset and assign them to the dataset."""
        entries: Set[EntryTuple] = set()
        for language in ["en", "fi"]:
            entries.update(self._get_access_types(dataset, language))
            entries.update(self._get_data_catalogs(dataset, language))
            entries.update(self._get_creators(dataset, language))
            entries.update(self._get_organizations(dataset, language))
            entries.update(self._get_keywords(dataset, language))
            entries.update(self._get_reference_data(dataset, language, "field_of_science"))
            entries.update(self._get_reference_data(dataset, language, "infrastructure"))
            entries.update(self._get_file_types(dataset, language))
            entries.update(self._get_projects(dataset, language))

        if not entries:
            dataset.index_entries.clear()
            return []

        # Get or create instances and link them to the dataset
        existing_instances = self._get_existing_instances(entries)
        existing_as_set = set(EntryTuple.from_entries(existing_instances))
        missing = entries - existing_as_set
        new_instances = self.create_from_tuples(missing)
        all_instances = existing_instances + new_instances

        dataset.index_entries.set(all_instances)
        return all_instances


class DatasetIndexEntry(models.Model):
    """Index for faceted filtering of datasets.

    Stores values used in aggregation of datasets.
    Each key-value-language tuple is unique and shared across
    all related datasets.
    """

    objects = DatasetIndexEntryManager()

    id = models.AutoField(primary_key=True, editable=False)
    key = models.TextField(help_text="Facet type, e.g. 'creator'", editable=False)
    value = models.TextField(editable=False)
    language = models.TextField(help_text="Language code, e.g. 'en' or 'fi'", editable=False)
    datasets = models.ManyToManyField("Dataset", related_name="index_entries")

    def __str__(self):
        return f"{self.language}-{self.key}-{self.value}"

    class Meta:
        ordering = ["key", "value", "language"]
        # Make sure (value, key, language) tuples are unique. This also creates
        # an index that can be used when querying objects by
        # (value), (value, key), or (value, key, language)
        constraints = [
            models.UniqueConstraint(
                fields=("value", "key", "language"), name="unique-lang-key-value"
            ),
        ]
