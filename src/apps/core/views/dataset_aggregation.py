import logging

from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber

from apps.common.helpers import parse_csv_string, single_translation
from apps.core.models import DataService, DatasetIndexEntry

logger = logging.getLogger(__name__)


def _get_facet_search_params(request):
    facet_search_params: dict[str, str] = {
        "project": request.query_params.get("project_facet_search"),
        "creator": request.query_params.get("creator_facet_search"),
        "organization": request.query_params.get("organization_facet_search"),
        "field_of_science": request.query_params.get("field_of_science_facet_search"),
        "keyword": request.query_params.get("keyword_facet_search"),
    }
    return {k: v for k, v in facet_search_params.items() if v}


def aggregate_queryset(queryset, request):
    dataset_ids = list(queryset.values_list("id", flat=True))
    language = request.query_params.get("filter_language")
    expand_data_services = request.query_params.get("expand_data_services")
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

    def get_data_services_by_catalog_label():
        if str(expand_data_services).lower() != "true":
            return {}

        services_by_catalog_label = {}
        service_entries = (
            DataService.objects.filter(
                remoteresource__dataset_id__in=dataset_ids,
            )
            .annotate(dataset_count=Count("remoteresource__dataset_id", distinct=True))
            .distinct()
            .select_related("catalog")
        )
        for service in service_entries:
            catalog_label = single_translation(service.catalog.title, language)
            service_label = single_translation(service.pref_label, language)
            if not catalog_label or not service_label:
                continue
            services = services_by_catalog_label.setdefault(catalog_label, [])
            services.append({"value": {language: service_label}, "count": service.dataset_count})

        return services_by_catalog_label

    data_services_by_catalog_label = get_data_services_by_catalog_label()

    # If the query includes parameters related to aggregate facets, store
    # the parameters so that each facet is saved as its own key, and any
    # associated value or values are stored as a list under that key.
    # The resulting list includes both:
    # - AND cases: multiple occurrences of the same query parameter key:
    #   retrieved via getlist(), e.g. ?keyword=cat&keyword=dog
    # - OR cases: a single parameter value containing a comma-separated list:
    #   parsed via parse_csv_string(), e.g. ?keyword=cat,dog or
    #   ?keyword="cat, domestic","dog"
    existing_aggregate_query_params: dict[str, list[str]] = {}
    for query_param_key in request.query_params.keys():
        if query_param_key in facet_query_params.values():
            raw_values: list[str] = request.query_params.getlist(query_param_key)
            values: list[str] = []
            for value in raw_values:
                values += parse_csv_string(value)

            # Remove duplicate occurences by converting to a set and back to
            # a list:
            existing_aggregate_query_params[query_param_key] = list(set(values))

    if has_facet_search_params():
        return {
            facet: {
                "query_parameter": facet_query_params.get(facet),
                "hits": get_hits(facet),
            }
            for facet in facet_search_params.keys()
        }
    else:
        # If the query includes parameters for a facet whose hits don't
        # contain any aggregates, return the values provided in the query
        # as dictionary items in the facet's hits list with a count of 0.
        # This ensures that if an aggregate/filter item was selected and a
        # another query parameter is added afterward, the Etsin UI still
        # shows the aggregate/filter item as selected (with a count of 0)
        # even when no datasets match it anymore.

        # Otherwise, retrieve all aggregate items related to the facet.
        facets_response = {}
        for facet, query_parameter in facet_query_params.items():
            hits = get_hits(facet)

            if query_parameter in existing_aggregate_query_params and len(hits) == 0:
                hits = []
                for aggregate in existing_aggregate_query_params[query_parameter]:
                    hits.append(
                        {
                            "value": {language: aggregate},
                            "count": 0,
                        }
                    )
            elif facet == "data_catalog" and data_services_by_catalog_label:
                hits_with_data_services = []
                for hit in hits:
                    catalog_label = hit["value"].get(language)
                    hits_with_data_services.append(
                        {
                            **hit,
                            "data_service": data_services_by_catalog_label.get(catalog_label, []),
                        }
                    )
                hits = hits_with_data_services

            facets_response[facet] = {
                "query_parameter": query_parameter,
                "hits": hits,
            }

        return facets_response
