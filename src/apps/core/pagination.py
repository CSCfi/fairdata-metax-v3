import logging
from collections import Counter

from django.db.models import Count, F, Func, Q

from apps.actors.models import Organization
from apps.common.pagination import OffsetPagination
from apps.core.models import (
    AccessType,
    DataCatalog,
    Dataset,
    DatasetActor,
    DatasetProject,
    FieldOfScience,
    ResearchInfra,
)
from apps.refdata.models import FileType

logger = logging.getLogger(__name__)


class AggregatingDatasetPagination(OffsetPagination):
    def aggregate_queryset(self, queryset):
        dataset_ids = list(queryset.values_list("id", flat=True))

        return {
            "data_catalog": self._wrap_into_aggregation_object(
                query_parameter="data_catalog__title",
                hits=self._aggregate_data_catalog(dataset_ids),
            ),
            "access_type": self._wrap_into_aggregation_object(
                query_parameter="access_rights__access_type__pref_label",
                hits=self._aggregate_access_type(dataset_ids),
            ),
            "organization": self._wrap_into_aggregation_object(
                query_parameter="actors__organization__pref_label",
                hits=self._aggregate_organizations(dataset_ids=dataset_ids),
            ),
            "creator": self._wrap_into_aggregation_object(
                query_parameter="actors__roles__creator",
                hits=self._aggregate_creator(dataset_ids),
            ),
            "field_of_science": self._wrap_into_aggregation_object(
                query_parameter="field_of_science__pref_label",
                hits=self._aggregate_field_of_science(dataset_ids),
            ),
            "keyword": self._wrap_into_aggregation_object(
                query_parameter="keyword", hits=self._aggregate_keyword(dataset_ids)
            ),
            "infrastructure": self._wrap_into_aggregation_object(
                query_parameter="infrastructure__pref_label",
                hits=self._aggregate_infrastructure(dataset_ids),
            ),
            "file_type": self._wrap_into_aggregation_object(
                query_parameter="file_type", hits=self._aggregate_file_type(dataset_ids)
            ),
            "project": self._wrap_into_aggregation_object(
                query_parameter="projects__title", hits=self._aggregate_project(dataset_ids)
            ),
        }

    def _wrap_into_aggregation_object(self, query_parameter, hits):
        return {"query_parameter": query_parameter, "hits": hits}

    def _aggregate_ref_data(self, dataset_ids, model, field_name, dataset_access, languages):
        if languages is None:
            return self._aggregate_ref_data_by_field_name(
                dataset_ids=dataset_ids,
                model=model,
                field_name=field_name,
                dataset_access=dataset_access,
            )

        items_by_lang = [
            self._aggregate_ref_data_by_lang(
                dataset_ids=dataset_ids,
                model=model,
                field_name=field_name,
                dataset_access=dataset_access,
                lang=lang,
            )
            for lang in languages
        ]
        return [item for items in items_by_lang for item in items]

    def _aggregate_ref_data_by_field_name(self, dataset_ids, model, field_name, dataset_access):
        filter_args = {f"{dataset_access}__in": dataset_ids}

        items_und = (
            model.available_objects.filter(**filter_args)
            .values(value=F(f"{field_name}"), count=Count("*"))
            .order_by("-count")[:20]
        )

        return [{"value": item["value"], "count": item["count"]} for item in items_und]

    def _aggregate_ref_data_by_lang(self, dataset_ids, model, field_name, dataset_access, lang):
        filter_args = {f"{dataset_access}__in": dataset_ids}

        items = (
            model.available_objects.filter(**filter_args)
            .values(value=F(f"{field_name}__{lang}"), count=Count("*"))
            .filter(value__isnull=False, count__gt=0)
            .order_by("-count")[:20]
        )

        return [{"value": {f"{lang}": item["value"]}, "count": item["count"]} for item in items]

    def _aggregate_data_catalog(self, dataset_ids):
        return self._aggregate_ref_data(
            dataset_ids=dataset_ids,
            model=DataCatalog,
            field_name="title",
            dataset_access="records",
            languages=None,
        )

    def _aggregate_access_type(self, dataset_ids):
        return self._aggregate_ref_data(
            dataset_ids=dataset_ids,
            model=AccessType,
            field_name="pref_label",
            dataset_access="access_rights__datasets",
            languages=["fi", "en"],
        )

    def _aggregate_field_of_science(self, dataset_ids):
        return self._aggregate_ref_data(
            dataset_ids=dataset_ids,
            model=FieldOfScience,
            field_name="pref_label",
            dataset_access="datasets",
            languages=["fi", "en"],
        )

    def _aggregate_infrastructure(self, dataset_ids):
        return self._aggregate_ref_data(
            dataset_ids=dataset_ids,
            model=ResearchInfra,
            field_name="pref_label",
            dataset_access="datasets",
            languages=["fi", "en"],
        )

    def _aggregate_organizations(self, dataset_ids):
        """
        Aggragate hits and names for organizations (top level only) per dataset.
        Organization can appear multiple times in different roles per dataset.
        """

        return self._get_organizations(dataset_ids=dataset_ids, get_root_orgs=False)[:40]

    def _aggregate_creator(self, dataset_ids):
        orgs = self._get_organizations(
            dataset_ids=dataset_ids,
            filters={"actor_organizations__datasetactor__roles__icontains": "creator"},
        )

        persons = (
            DatasetActor.available_objects.filter(
                Q(roles__icontains="creator") & Q(person__isnull=False),
                dataset__in=dataset_ids,
            )
            .annotate(_dataset=F("dataset"))
            .values(translated=F("person__name"))
            .order_by("translated")
            .annotate(count=Count("_dataset", distinct=True))
            .filter(count__gt=0, translated__isnull=False)
        )
        persons = sorted(persons, key=lambda p: p["translated"])[:40]
        persons = [
            {"value": {"und": person["translated"]}, "count": person["count"]}
            for person in persons
        ]

        creators = orgs + persons
        return sorted(creators, key=lambda c: -c["count"])[:40]

    def _aggregate_keyword(self, dataset_ids):
        keywords = (
            Dataset.available_objects.filter(id__in=dataset_ids)
            .annotate(name=Func(F("keyword"), function="unnest"))
            .values_list("name")
            .order_by("name")
            .values("name", count=Count("*"))
            .order_by("-count")[:20]
        )

        return [
            {"value": {"und": keyword["name"]}, "count": keyword["count"]} for keyword in keywords
        ]

    def _aggregate_file_type(self, dataset_ids):
        return self._aggregate_ref_data(
            dataset_ids=dataset_ids,
            model=FileType,
            field_name="pref_label",
            dataset_access="filesetfilemetadata__file_set__dataset",
            languages=["fi", "en"],
        )

    def _aggregate_project(self, dataset_ids):
        projects_en = self._get_project_by_language(dataset_ids, "en")[:40]
        projects_fi = self._get_project_by_language(dataset_ids, "fi")[:40]
        projects_und = self._get_project_by_language(dataset_ids, "und")[:40]

        return projects_fi + projects_en + projects_und

    def _get_project_by_language(self, dataset_ids, language):
        projects = (
            DatasetProject.available_objects.values(
                pref_label=F(f"title__{language}"),
            )
            .order_by()
            .distinct()
            .annotate(count=Count("dataset", filter=Q(dataset__id__in=dataset_ids), distinct=True))
            .filter(count__gt=0, pref_label__isnull=False)
            .order_by("-count")
        )

        return [
            {"value": {language: project["pref_label"]}, "count": project["count"]}
            for project in projects
        ]

    def _get_organizations(self, dataset_ids, filters={}, get_root_orgs=False):
        orgs = Organization.all_objects.filter(
            **filters, actor_organizations__datasetactor__dataset__in=dataset_ids
        )

        if get_root_orgs:
            orgs = self._get_root_level_orgs(orgs)

        orgs_fi = sorted(
            self._get_organizations_by_lang(orgs=orgs, lang="fi"),
            key=lambda o: -o["count"],
        )[:40]

        orgs_en = sorted(
            self._get_organizations_by_lang(orgs=orgs, lang="en"),
            key=lambda o: -o["count"],
        )[:40]

        orgs = orgs_fi + orgs_en
        return orgs

    def _get_organizations_by_lang(self, orgs, lang):
        lang_filtered_orgs = (
            orgs.annotate(
                dataset=F("actor_organizations__datasetactor__dataset"),
            )
            .values(
                translated=F(f"pref_label__{lang}"),
            )
            .filter(translated__isnull=False)
            .order_by("translated")
            .annotate(count=Count("dataset", distinct=True))
            .filter(count__gt=0, translated__isnull=False)
        )

        return [
            {"value": {lang: org["translated"]}, "count": org["count"]}
            for org in lang_filtered_orgs
        ]

    def _get_root_level_orgs(self, orgs):
        """Get root level of the orgs"""
        root_level_orgs = orgs.filter(parent__isnull=True)
        orgs_with_parent = orgs.filter(parent__isnull=False)

        while len(orgs_with_parent):
            parent_ids = list(orgs_with_parent.values_list("parent", flat=True))
            sub_level_orgs = Organization.available_objects.filter(id__in=parent_ids)
            root_level_orgs = root_level_orgs | sub_level_orgs
            orgs_with_parent = sub_level_orgs.filter(parent__isnull=False)

        return root_level_orgs
