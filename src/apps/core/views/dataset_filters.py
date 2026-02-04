import logging
import operator
from functools import reduce
from typing import List

from django.core.cache import caches
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.fields import CSVWidget
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from watson import search

from apps.common.filters import MultipleCharField, MultipleCharFilter, VerboseChoiceFilter
from apps.common.helpers import is_valid_uuid
from apps.core.models.catalog_record import Dataset
from apps.core.models.concepts import AccessType
from apps.core.models.data_catalog import DataCatalog
from apps.core.models.preservation import Preservation
from apps.core.permissions import DatasetAccessPolicy
from apps.core.views.common_views import DefaultValueOrdering


logger = logging.getLogger(__name__)
serialized_datasets_cache = caches["serialized_datasets"]


class DatasetIndexEntryFilter(filters.MultipleChoiceFilter):
    """Filter datasets by DatasetIndexEntry using key."""

    field_class = MultipleCharField

    def __init__(self, *args, key: str, **kwargs):
        self.key = key
        kwargs.setdefault("label", f"Filter datasets by value of facet {key}.")
        super().__init__(*args, **kwargs)

    def get_request(self):
        try:
            return self.parent.request
        except AttributeError:
            return None

    def filter(self, qs, value):
        if not value:
            return qs

        # The only thing the filter needs from the "core_dataset" table is the dataset id which
        # already exists in the M2M table. Using the through model directly avoids
        # joining on "core_dataset" in subqueries, which improves the filtering performance
        # a lot when there are lots of filters.
        through_model = Dataset._meta.get_field("index_entries").through

        # Filter by language query parameter when set
        lang_filter = Q()
        request = self.get_request()
        if request and (lang := request.GET.get("language")):
            lang_filter = Q(datasetindexentry__language=lang)

        # Do an Exists() query for each "AND" condition
        for group in value:
            index_query = through_model.objects.filter(dataset_id=OuterRef("id"))
            union = Q()
            for val in group:
                union |= Q(
                    lang_filter, datasetindexentry__key=self.key, datasetindexentry__value=val
                )
            index_query = index_query.filter(union)
            qs = qs.filter(Exists(index_query))

        return qs


class DatasetFilter(filters.FilterSet):
    access_rights__access_type__pref_label = MultipleCharFilter(
        method="filter_access_type",
        label="access_type",
    )

    actors__organization__pref_label = MultipleCharFilter(
        method="filter_organization",
        label="organization name",
    )

    actors__person__name = MultipleCharFilter(
        max_length=512,
        lookup_expr="icontains",
        label="person name",
    )

    actors__role = MultipleCharFilter(
        field_name="actors__roles",
        max_length=512,
        lookup_expr="icontains",
        label="actor role",
        conjoined=True,
        widget=CSVWidget,
    )

    actors__roles__creator = MultipleCharFilter(method="filter_creator", max_length=255)

    data_catalog__id = MultipleCharFilter(
        field_name="data_catalog__id",
        lookup_expr="icontains",
        label="data-catalog identifier",
        help_text="filter with substring from data-catalog identifier",
    )

    data_catalog__title = filters.CharFilter(
        field_name="data_catalog__title__values",
        max_length=512,
        lookup_expr="icontains",
        label="data-catalog title",
    )

    deprecated = filters.BooleanFilter(lookup_expr="isnull", exclude=True)

    field_of_science__pref_label = MultipleCharFilter(
        method="filter_field_of_science",
        label="field of science",
    )

    file_type = MultipleCharFilter(
        method="filter_file_type",
        label="file_type",
    )

    id = MultipleCharFilter(
        label="id",
        field_name="id",
        method="filter_id",
    )

    infrastructure__pref_label = MultipleCharFilter(
        method="filter_infrastructure",
        label="infrastructure",
    )

    keyword = MultipleCharFilter(method="filter_keyword", label="keyword")

    metadata_owner__organization = MultipleCharFilter(
        method="filter_metadata_owner_organization",
        max_length=512,
        label="metadata owner organization",
    )

    metadata_owner__user = filters.CharFilter(
        field_name="metadata_owner__user__username",
        max_length=512,
        lookup_expr="icontains",
        label="metadata owner user",
    )

    ordering = DefaultValueOrdering(
        fields=(
            ("created", "created"),
            ("modified", "modified"),
            ("preservation__state", "preservation_state"),  # Needed for FDDPS
            ("id", "id"),  # Needed for FDDPS
        ),
        default="-modified",
    )

    persistent_identifier = filters.CharFilter(
        max_length=255,
        lookup_expr="exact",
        label="persistent identifier",
    )

    preservation__contract = filters.CharFilter(
        max_length=512,
        label="preservation contract",
        field_name="preservation__contract",
    )

    preservation__state = MultipleCharFilter(
        method="filter_preservation_state",
        label="preservation_state",
        field_name="preservation__state",
    )

    projects__title = MultipleCharFilter(
        method="filter_project",
        label="projects",
    )

    publishing_channels = VerboseChoiceFilter(
        choices=[
            ("default", "default"),
            ("etsin", "etsin"),
            ("ttv", "ttv"),
            ("all", "all"),
            ("qvain", "qvain"),
        ],
        method="filter_publishing_channels",
        label="""publishing channels
        Filter datasets based on the publishing channels of the dataset's catalog.
        The default value is 'default'.
        """,
        help_text="""
        Filter datasets based on the publishing channels of the dataset's catalog.
        The default value is 'default'.
        """,
    )

    search = filters.CharFilter(method="search_dataset")

    state = filters.ChoiceFilter(
        choices=Dataset.StateChoices.choices,
        label="state",
    )

    temporal__end_date = filters.DateFilter(
        method="temporal_search",
        label="""temporal end date
        Filter datasets based on their temporal information.
        'temporal__end_date' can be used together with 'temporal__start_date' to filter datasets' which have temporal information that overlaps with given timerange.
        If only 'temporal__end_date' is given, all datasets are returned unless, the dataset's temporal's start_date is after the given 'temporal__end_date'
        """,
        help_text="""
        Filter datasets based on their temporal information.
        'temporal__end_date' can be used together with 'temporal__start_date' to filter datasets' which have temporal information that overlaps with given timerange.
        If only 'temporal__end_date' is given, all datasets are returned unless, the dataset's temporal's start_date is after the given 'temporal__end_date'
        """,
    )

    temporal__start_date = filters.DateFilter(
        method="temporal_search",
        label="""temporal start date
        Filter datasets based on their temporal information.
        'temporal__start_date' can be used together with 'temporal__end_date' to filter datasets' which have temporal information that overlaps with given timerange.
        If only 'temporal__start_date' is given, all datasets are returned unless, the dataset's temporal's end_date is before the given 'temporal__start_date'
        """,
        help_text="""
        Filter datasets based on their temporal information.
        'temporal__start_date' can be used together with 'temporal__end_date' to filter datasets' which have temporal information that overlaps with given timerange.
        If only 'temporal__start_date' is given, all datasets are returned unless, the dataset's temporal's end_date is before the given 'temporal__start_date'
        """,
    )

    title = filters.CharFilter(
        field_name="title__values",
        max_length=512,
        lookup_expr="icontains",
        label="title",
    )

    def temporal_search(self, queryset, name, value):
        # DateFilter is used only for swagger and validating the query params.
        # The actual filtering is dependent on both start_date and end_date
        # so it is done in filter_queryset.
        return queryset

    def search_dataset(self, queryset, name, value):
        if value is None or value == "":
            return queryset
        if self.form.cleaned_data.get("ordering") is None:
            return search.filter(queryset=queryset, search_text=value, ranking=True)
        return search.filter(queryset=queryset, search_text=value, ranking=False)

    def filter_access_type(self, queryset, name, value):
        access_types = list(
            self._filter_list(
                queryset=AccessType.objects.order_by().values_list("id", flat=True),
                value=value,
                filter_param="pref_label__values__icontains",
            )
        )
        return queryset.filter(access_rights__access_type__in=access_types)

    def filter_organization(self, queryset, name, value):
        org_query = Dataset.all_objects.filter(id=OuterRef("id"))
        for group in value:
            union = reduce(
                operator.or_,
                (
                    (
                        Q(actors__organization__pref_label__values__icontains=x)
                        | Q(actors__organization__parent__pref_label__values__icontains=x)
                        | Q(actors__organization__parent__parent__pref_label__values__icontains=x)
                    )
                    for x in group
                ),
            )
            org_query = org_query.filter(union)
        return queryset.filter(Exists(org_query))

    def filter_keyword(self, queryset, name, value):
        return self._filter_list(queryset, value, filter_param="keyword__icontains")

    def filter_creator(self, queryset, name, value):
        creator_query = Dataset.all_objects.filter(id=OuterRef("id"))
        for group in value:
            if not group:
                continue
            union = Q()
            for val in group:
                union = union | (
                    Q(actors__roles__contains=["creator"])
                    & (
                        Q(actors__organization__pref_label__values__contains=[val])
                        | Q(actors__organization__parent__pref_label__values__contains=[val])
                        | Q(
                            actors__organization__parent__parent__pref_label__values__contains=[
                                val
                            ]
                        )
                        | Q(actors__person__name__exact=val)
                    )
                )
            creator_query = creator_query.filter(union)
        return queryset.filter(Exists(creator_query))

    def filter_field_of_science(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="field_of_science__pref_label__values__icontains",
        )

    def filter_infrastructure(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="infrastructure__pref_label__values__icontains",
        )

    def filter_file_type(self, queryset, name, value):
        return self._filter_list(
            queryset,
            value,
            filter_param="file_set__file_metadata__file_type__pref_label__values__icontains",
        )

    def filter_project(self, queryset, name, value):
        return self._filter_list(
            queryset, value, filter_param="projects__title__values__icontains"
        )

    def filter_publishing_channels(self, queryset, name, value):
        if value == "all":
            return queryset
        if value in ["etsin", "ttv"]:
            # Show PAS datasets only when preservation state is 120
            queryset = queryset.filter(state=Dataset.StateChoices.PUBLISHED).filter(
                ~Q(data_catalog__id="urn:nbn:fi:att:data-catalog-pas")
                | Q(preservation__state=Preservation.PreservationState.IN_PAS)
            )

        catalog_ids = list(
            DataCatalog.objects.filter(publishing_channels__contains=[value]).values_list(
                "id", flat=True
            )
        )
        if value in {"default", "qvain"}:
            # Default and qvain include drafts without catalogs
            return queryset.filter(
                Q(data_catalog_id__in=catalog_ids) | Q(data_catalog__isnull=True)
            )
        return queryset.filter(data_catalog_id__in=catalog_ids)

    def filter_preservation_state(self, queryset, name, value):
        result = queryset
        for states in value:
            invalid_states = [
                state
                for state in states
                if not state.lstrip("-").isdigit()
                or int(state) not in Preservation.PreservationState
            ]

            if invalid_states:
                raise ValidationError(
                    {
                        "preservation": {
                            "state": (
                                f"The following states are not valid: "
                                f"{', '.join(invalid_states)}"
                            )
                        }
                    }
                )

            state_query = Q(preservation__state__in=states)

            # If dataset's preservation entry does not exist, it's considered
            # to have the default value -1 (NONE)
            if str(Preservation.PreservationState.NONE) in states:
                result = result.filter(state_query | Q(preservation__isnull=True))
            else:
                result = result.filter(state_query)
        return result.distinct()

    def filter_id(self, queryset, name, value):
        if value is None or value == "":
            return queryset
        result = queryset
        for ids in value:
            failing_ids = [id for id in ids if not is_valid_uuid(id)]
            if failing_ids:
                raise exceptions.ValidationError(
                    {"id": f"Dataset identifiers must be valid UUIDs. Invalid IDs: {failing_ids}"}
                )
            result = result.filter(id__in=ids)
        return result.distinct()

    def filter_metadata_owner_organization(self, queryset, name, value):
        result = queryset
        for groups in value:
            union = reduce(
                operator.or_, (Q(metadata_owner__organization__exact=x) for x in groups)
            )
            result = result.filter(union)
        return result.distinct()

    def _filter_list(self, queryset: QuerySet, value: List[List[str]], filter_param: str):
        result = queryset
        for group in value:
            union = reduce(operator.or_, (Q(**{filter_param: x}) for x in group))
            result = result.filter(union)
        return result.distinct()

    has_files = filters.BooleanFilter(
        field_name="file_set__files", lookup_expr="isnull", exclude=True, distinct=True
    )
    csc_projects = filters.BaseInFilter(field_name="file_set__storage__csc_project")
    storage_services = filters.BaseInFilter(field_name="file_set__storage__storage_service")

    only_owned_or_shared = filters.BooleanFilter(method="filter_owned_or_shared")

    only_admin = filters.BooleanFilter(method="filter_only_admin")

    def filter_owned_or_shared(self, queryset, name, value):
        """Filter datasets owned by or shared with the authenticated user."""
        if value:
            return DatasetAccessPolicy.scope_queryset_owned_or_shared(self.request, queryset)
        return queryset

    def filter_only_admin(self, queryset, name, value):
        """Filter datasets the authenticated user is an admin of."""
        if value:
            return DatasetAccessPolicy.scope_queryset_admin(self.request, queryset)
        return queryset

    def filter_queryset(self, queryset):
        # Use "etsin" as the default publishing channel filter value
        if not self.form.cleaned_data["publishing_channels"]:
            self.form.cleaned_data["publishing_channels"] = "default"
        queryset = self.filter_temporals(queryset)
        return super().filter_queryset(queryset)

    def filter_temporals(self, queryset):
        query_params = self.form.cleaned_data
        end_date = query_params["temporal__end_date"]
        start_date = query_params["temporal__start_date"]

        if end_date == None and start_date == None:
            return queryset

        if end_date == None:
            queryset = queryset.filter(
                Q(temporal__start_date__isnull=False, temporal__end_date__isnull=True)
                | Q(temporal__end_date__gte=start_date)
            ).distinct()
            return queryset

        if start_date == None:
            queryset = queryset.filter(
                Q(temporal__start_date__isnull=True, temporal__end_date__isnull=False)
                | Q(temporal__start_date__lte=end_date)
            ).distinct()
            return queryset

        if end_date < start_date:
            raise ValidationError(
                {
                    "temporal__end_date": "temporal__end_date must not be before temporal__start_date"
                }
            )

        queryset = queryset.filter(
            Q(temporal__start_date__lte=end_date, temporal__end_date__gte=start_date)
            | Q(temporal__start_date__isnull=True, temporal__end_date__gte=start_date)
            | Q(temporal__end_date__isnull=True, temporal__start_date__lte=end_date)
        ).distinct()
        return queryset

    # Facet filters
    facet_access_type = DatasetIndexEntryFilter(key="access_type")
    facet_creator = DatasetIndexEntryFilter(key="creator")
    facet_data_catalog = DatasetIndexEntryFilter(key="data_catalog")
    facet_field_of_science = DatasetIndexEntryFilter(key="field_of_science")
    facet_file_type = DatasetIndexEntryFilter(key="file_type")
    facet_infrastructure = DatasetIndexEntryFilter(key="infrastructure")
    facet_keyword = DatasetIndexEntryFilter(key="keyword")
    facet_organization = DatasetIndexEntryFilter(key="organization")
    facet_project = DatasetIndexEntryFilter(key="project")
