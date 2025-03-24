from unittest.mock import patch

from django.db import transaction
from watson.management.commands.buildwatson import (
    Command as BuildWatsonCommand,
    _bulk_save_search_entries,
    force_str,
    get_engine,
)

from apps.common.profiling import count_queries
from apps.core.models import Dataset


orig_get_queryset = Dataset.objects.get_queryset


def rebuild_index_for_model(
    model_, engine_slug_, verbosity_, slim_=False, batch_size_=100, non_atomic_=False
):
    """rebuilds index for a model

    Patched from original function to add:
    - prefetching Dataset relations used in search
    - iterator chunk_size (iterator does not support prefetch_related without chunk_size)
    """

    search_engine_ = get_engine(engine_slug_)

    local_refreshed_model_count = [0]  # HACK: Allows assignment to outer scope.

    def iter_search_entries():
        # Only index specified objects if slim_ is True
        if slim_ and search_engine_._registered_models[model_].get_live_queryset():
            obj_list = search_engine_._registered_models[model_].get_live_queryset()
        else:
            obj_list = model_._default_manager.all()

        # --- Changes start ---
        if model_ == Dataset:
            obj_list = obj_list.prefetch_related(
                "actors",
                "actors__person",
                "actors__organization",
                "actors__organization__parent",
                "actors__organization__parent__parent",
                "other_identifiers",
                "relation",
                "relation__entity",
                "theme",
            )

        for obj in obj_list.iterator(chunk_size=1000):
            # --- Changes end ---
            for search_entry in search_engine_._update_obj_index_iter(obj):
                yield search_entry
            local_refreshed_model_count[0] += 1
            if verbosity_ >= 3:
                print(
                    "Refreshed search entry for {model} {obj} "
                    "in {engine_slug!r} search engine.".format(
                        model=force_str(model_._meta.verbose_name),
                        obj=force_str(obj),
                        engine_slug=force_str(engine_slug_),
                    )
                )
        if verbosity_ == 2:
            print(
                "Refreshed {local_refreshed_model_count} {model} search entry(s) "
                "in {engine_slug!r} search engine.".format(
                    model=force_str(model_._meta.verbose_name),
                    local_refreshed_model_count=local_refreshed_model_count[0],
                    engine_slug=force_str(engine_slug_),
                )
            )

    if non_atomic_:
        search_engine_.cleanup_model_index(model_)
        _bulk_save_search_entries(iter_search_entries(), batch_size=batch_size_)
    else:
        with transaction.atomic():
            search_engine_.cleanup_model_index(model_)
            _bulk_save_search_entries(iter_search_entries(), batch_size=batch_size_)
    return local_refreshed_model_count[0]


class Command(BuildWatsonCommand):

    def handle(self, *args, **options):
        """Patched buildwatson with optimizations for dataset handling."""

        with patch(
            "watson.management.commands.buildwatson.rebuild_index_for_model",
            rebuild_index_for_model,
        ):
            super().handle(*args, **options)
