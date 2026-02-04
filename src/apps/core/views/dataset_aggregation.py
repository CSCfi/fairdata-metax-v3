import logging

from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber

from apps.core.models import DatasetIndexEntry

logger = logging.getLogger(__name__)


def _get_facet_search_params(request):
    facet_search_params = {
        "project": request.query_params.get("project_facet_search"),
        "creator": request.query_params.get("creator_facet_search"),
        "organization": request.query_params.get("organization_facet_search"),
        "field_of_science": request.query_params.get("field_of_science_facet_search"),
        "keyword": request.query_params.get("keyword_facet_search"),
    }
    return {k: v for k, v in facet_search_params.items() if v}


# /datasets/aggregates?language=fi&project_facet_search=test


def aggregate_queryset(queryset, request):
    dataset_ids = list(queryset.values_list("id", flat=True))
    language = request.query_params.get("language")
    facet_search_params = _get_facet_search_params(request)
    limit_hits = request.query_params.get("limit_hits", 20)

    facet_query_params = {
        "data_catalog": "facet_data_catalog",
        "access_type": "facet_access_type",
        "organization": "facet_organization",
        "creator": "facet_creator",
        "field_of_science": "facet_field_of_science",
        "keyword": "facet_keyword",
        "infrastructure": "facet_infrastructure",
        "file_type": "facet_file_type",
        "project": "facet_project",
    }

    filters = Q()

    def has_facet_search_params():
        return len(facet_search_params.keys()) > 0

    if has_facet_search_params():
        for facet, value in facet_search_params.items():
            filters |= Q(key=facet, value__icontains=value)
    else:
        for facet in facet_query_params.keys():
            filters |= Q(key=facet)

    entries = (
        DatasetIndexEntry.objects.filter(datasets__in=dataset_ids, language=language)
        .values("key", "value")
        .filter(filters)
        .annotate(dataset_count=Count("datasets"))
        .annotate(
            # Determine row numbers partitioned by key, largest dataset count first
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F("key")],
                order_by=F("dataset_count").desc(),
            )
        )
        .filter(row_number__lte=limit_hits)
        .values("key", "value", "dataset_count")
    )

    # Group aggregated results by key, e.g.
    # {
    #   "access_type": [
    #     { "value": "Open", "count": 3560 }, ...
    #   ],
    #    ...
    # }
    result = {}
    for entry in entries:
        key_results = result.setdefault(entry["key"], [])
        key_results.append({"value": entry["value"], "count": entry["dataset_count"]})

    # Convert results to shape expected by etsin
    def get_hits(key):
        return [
            {"value": {language: entry["value"]}, "count": entry["count"]}
            for entry in result.get(key, [])
        ]

    if has_facet_search_params():
        return {
            facet: {
                "query_parameter": facet_query_params[facet],
                "hits": get_hits(facet),
            }
            for facet in facet_search_params.keys()
        }
    else:
        return {
            facet: {
                "query_parameter": query_parameter,
                "hits": get_hits(facet),
            }
            for facet, query_parameter in facet_query_params.items()
        }
