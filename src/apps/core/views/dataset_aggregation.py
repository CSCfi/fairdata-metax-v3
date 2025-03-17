import logging

from django.db.models import Count, F, Func, Q
from django.db.models.functions import Coalesce

from apps.actors.models import Organization
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


def aggregate_queryset(queryset):
    dataset_ids = list(queryset.values_list("id", flat=True))

    return {
        "data_catalog": _wrap_into_aggregation_object(
            query_parameter="data_catalog__title",
            hits=_aggregate_data_catalog(dataset_ids),
        ),
        "access_type": _wrap_into_aggregation_object(
            query_parameter="access_rights__access_type__pref_label",
            hits=_aggregate_access_type(dataset_ids),
        ),
        "organization": _wrap_into_aggregation_object(
            query_parameter="actors__organization__pref_label",
            hits=_aggregate_organizations(dataset_ids=dataset_ids),
        ),
        "creator": _wrap_into_aggregation_object(
            query_parameter="actors__roles__creator",
            hits=_aggregate_creator(dataset_ids),
        ),
        "field_of_science": _wrap_into_aggregation_object(
            query_parameter="field_of_science__pref_label",
            hits=_aggregate_field_of_science(dataset_ids),
        ),
        "keyword": _wrap_into_aggregation_object(
            query_parameter="keyword", hits=_aggregate_keyword(dataset_ids)
        ),
        "infrastructure": _wrap_into_aggregation_object(
            query_parameter="infrastructure__pref_label",
            hits=_aggregate_infrastructure(dataset_ids),
        ),
        "file_type": _wrap_into_aggregation_object(
            query_parameter="file_type", hits=_aggregate_file_type(dataset_ids)
        ),
        "project": _wrap_into_aggregation_object(
            query_parameter="projects__title", hits=_aggregate_project(dataset_ids)
        ),
    }


def _wrap_into_aggregation_object(query_parameter, hits):
    return {"query_parameter": query_parameter, "hits": hits}


def _aggregate_ref_data(dataset_ids, model, field_name, dataset_access, limit=20):
    filter_args = {f"{dataset_access}__in": dataset_ids}
    items = (
        model.available_objects.filter(**filter_args)
        .values(value=F(f"{field_name}"), count=Count("*"))
        .order_by("-count")[:limit]
    )
    return [{"value": item["value"], "count": item["count"]} for item in items]


def _aggregate_data_catalog(dataset_ids):
    return _aggregate_ref_data(
        dataset_ids=dataset_ids,
        model=DataCatalog,
        field_name="title",
        dataset_access="datasets",
        limit=100,
    )


def _aggregate_access_type(dataset_ids):
    return _aggregate_ref_data(
        dataset_ids=dataset_ids,
        model=AccessType,
        field_name="pref_label",
        dataset_access="access_rights__dataset",
    )


def _aggregate_field_of_science(dataset_ids):
    return _aggregate_ref_data(
        dataset_ids=dataset_ids,
        model=FieldOfScience,
        field_name="pref_label",
        dataset_access="datasets",
    )


def _aggregate_infrastructure(dataset_ids):
    return _aggregate_ref_data(
        dataset_ids=dataset_ids,
        model=ResearchInfra,
        field_name="pref_label",
        dataset_access="datasets",
    )


def _aggregate_organizations(dataset_ids):
    """
    Aggragate hits and names for organizations (top level only) per dataset.
    Organization can appear multiple times in different roles per dataset.
    """

    return _get_organizations(dataset_ids=dataset_ids)


def _aggregate_creator(dataset_ids):
    orgs = _get_organizations(
        dataset_ids=dataset_ids,
        filters={"actor_organizations__datasetactor__roles__icontains": "creator"},
    )

    persons = (
        DatasetActor.available_objects.filter(
            Q(roles__icontains="creator") & Q(person__isnull=False),
            dataset__in=dataset_ids,
        )
        .values(translated=F("person__name"))
        .annotate(count=Count("dataset", distinct=True))
        .order_by("-count")
    )[:40]
    persons = [
        {"value": {"und": person["translated"]}, "count": person["count"]} for person in persons
    ]
    creators = orgs + persons
    return sorted(creators, key=lambda c: -c["count"])[:40]


def _aggregate_keyword(dataset_ids):
    keywords = (
        Dataset.available_objects.filter(id__in=dataset_ids)
        .annotate(name=Func(F("keyword"), function="unnest"))
        .values_list("name")
        .order_by("name")
        .values("name", count=Count("*"))
        .order_by("-count")[:20]
    )

    return [{"value": {"und": keyword["name"]}, "count": keyword["count"]} for keyword in keywords]


def _aggregate_file_type(dataset_ids):
    return _aggregate_ref_data(
        dataset_ids=dataset_ids,
        model=FileType,
        field_name="pref_label",
        dataset_access="filesetfilemetadata__file_set__dataset",
    )


def _aggregate_project(dataset_ids):
    projects_en = _get_project_by_language(dataset_ids, "en")[:40]
    projects_fi = _get_project_by_language(dataset_ids, "fi")[:40]
    return projects_fi + projects_en


def _get_project_by_language(dataset_ids, language):
    projects = (
        DatasetProject.available_objects.values(
            pref_label=Coalesce(f"title__{language}", "title__und"),
        )
        .distinct()
        .annotate(count=Count("dataset", filter=Q(dataset__id__in=dataset_ids), distinct=True))
        .filter(count__gt=0, pref_label__isnull=False)
        .order_by("-count")
    )

    return [
        {"value": {language: project["pref_label"]}, "count": project["count"]}
        for project in projects
    ]


def _get_organizations(dataset_ids, filters={}):
    orgs = Organization.all_objects.filter(
        **filters, actor_organizations__datasetactor__dataset__in=dataset_ids
    )

    # Get topmost label in up to three organization levels
    orgs = orgs.annotate(
        aggregation_label=Coalesce(
            F("parent__parent__pref_label"), F("parent__pref_label"), F("pref_label")
        )
    )

    orgs_fi = sorted(
        _get_organizations_by_lang(orgs=orgs, lang="fi"),
        key=lambda o: -o["count"],
    )[:40]

    orgs_en = sorted(
        _get_organizations_by_lang(orgs=orgs, lang="en"),
        key=lambda o: -o["count"],
    )[:40]

    orgs = orgs_fi + orgs_en
    return orgs


def _get_organizations_by_lang(orgs, lang):
    lang_filtered_orgs = (
        orgs.annotate(
            dataset=F("actor_organizations__datasetactor__dataset"),
        )
        .values(
            # Get translation by lang, or try other languages if the primary choice isn't found
            translated=Coalesce(
                f"aggregation_label__{lang}",
                "aggregation_label__en",
                "aggregation_label__fi",
                "aggregation_label__sv",
                "aggregation_label__und",
            ),
        )
        .filter(translated__isnull=False)
        .order_by("translated")
        .annotate(count=Count("dataset", distinct=True))
        .filter(count__gt=0, translated__isnull=False)
    )

    return [
        {"value": {lang: org["translated"]}, "count": org["count"]} for org in lang_filtered_orgs
    ]
