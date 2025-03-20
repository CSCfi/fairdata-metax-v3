import logging

from django.conf import settings
from django.contrib import admin, messages
from django.db import models
from django.utils import timezone
from django_json_widget.widgets import JSONEditorWidget
from simple_history.admin import SimpleHistoryAdmin

from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
from apps.common.profiling import count_queries
from apps.common.tasks import run_task
from apps.core.models import (
    AccessRights,
    CatalogHomePage,
    Contract,
    DataCatalog,
    Dataset,
    DatasetActor,
    DatasetLicense,
    DatasetProject,
    DatasetPublisher,
    Entity,
    EntityRelation,
    FieldOfScience,
    FileSet,
    Funding,
    Language,
    LegacyDataset,
    MetadataProvider,
    OtherIdentifier,
    Provenance,
    RestrictionGrounds,
    Spatial,
    Temporal,
    Theme,
)
from apps.core.models.preservation import Preservation
from apps.core.models.sync import SyncAction, V2SyncStatus
from apps.core.signals import sync_dataset_to_v2

logger = logging.getLogger(__name__)


@admin.register(CatalogHomePage)
class CatalogHomePageAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DatasetPublisher)
class DatasetPublisherAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(AccessRights)
class AccessRightsAdmin(AbstractDatasetPropertyBaseAdmin):
    list_filter = ["created", "modified", "access_type", "restriction_grounds"]
    list_display = ["dataset", "access_type", "description"]
    autocomplete_fields = ["license"]
    list_select_related = ("dataset", "access_type")
    search_fields = ["dataset__id", "description__values", "access_type__pref_label__values"]


@admin.register(DataCatalog)
class DataCatalogAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "id",
        "dataset_versioning_enabled",
        "is_external",
    )
    list_filter = (
        "dataset_versioning_enabled",
        "is_external",
        "created",
        "modified",
    )
    autocomplete_fields = ("language",)


@admin.register(MetadataProvider)
class MetadataProviderAdmin(admin.ModelAdmin):
    list_display = ("user", "organization")
    list_filter = ("created", "modified")
    search_fields = ("organization", "user__username", "user__email")


class CoreRefDataAdminMixin:
    search_fields = ["pref_label__values", "url"]
    readonly_fields = ["broader"]
    list_filter = ("created", "modified")


@admin.register(Language)
class DatasetLanguage(CoreRefDataAdminMixin, admin.ModelAdmin):
    pass


@admin.register(Theme)
class DatasetTheme(CoreRefDataAdminMixin, admin.ModelAdmin):
    pass


@admin.register(FieldOfScience)
class DatasetFieldOfScience(CoreRefDataAdminMixin, admin.ModelAdmin):
    pass


@admin.register(Funding)
class Funding(admin.ModelAdmin):
    search_fields = ["funding_identifier"]
    list_filter = ("created", "modified")
    readonly_fields = ("funder",)


@admin.register(RestrictionGrounds)
class RestrictionGrounds(CoreRefDataAdminMixin, admin.ModelAdmin):
    pass


class V2SyncStatusInline(admin.StackedInline):
    model = V2SyncStatus
    readonly_fields = (
        "sync_started",
        "sync_files_started",
        "sync_stopped",
        "duration",
        "action",
        "error",
    )


@admin.register(Dataset)
class DatasetAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "title",
        "access_rights",
        "deprecated",
        "state",
        "data_catalog",
        "created",
        "modified",
    )
    list_filter = (
        "created",
        "modified",
        "issued",
        "deprecated",
        "state",
        "data_catalog",
    )
    autocomplete_fields = ["language", "theme", "field_of_science"]
    readonly_fields = (
        "preservation",
        "dataset_versions",
        "other_identifiers",
        "last_modified_by",
        "access_rights",
        "draft_of",
        "permissions",
    )
    list_select_related = ("access_rights", "data_catalog", "metadata_owner")
    search_fields = ["title__values", "keyword"]
    inlines = [V2SyncStatusInline]
    actions = ["sync_to_v2"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not settings.METAX_V2_INTEGRATION_ENABLED:
            actions.pop("sync_to_v2")
        return actions

    @admin.action(description="Sync datasets to V2", permissions=["change"])
    def sync_to_v2(self, request, queryset):
        datasets = Dataset.objects.filter(id__in=[item.id for item in queryset])
        datasets.prefetch_related(*Dataset.common_prefetch_fields)
        for dataset in datasets:
            run_task(sync_dataset_to_v2, dataset=dataset, action=SyncAction.UPDATE)
            self.message_user(
                request,
                f"{len(datasets)} datasets set to sync to V2",
                messages.SUCCESS,
            )

    def save_model(self, request, obj: Dataset, form, change):
        created = obj._state.adding
        super().save_model(request, obj, form, change)
        obj.signal_update(created=created)


@admin.register(DatasetActor)
class DatasetActorAdmin(admin.ModelAdmin):
    list_display = (
        "dataset",
        "actor",
        "roles",
    )
    list_filter = ("created", "modified")
    list_select_related = ("dataset",)
    autocomplete_fields = ["person", "organization", "dataset"]
    search_fields = (
        "dataset__id",
        "person__name",
        "person__email",
        "roles",
        "organization__pref_label__values",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("person", "organization", "dataset")

    def roles(self, obj):
        return ", ".join(o.name for o in obj.roles.all())

    def actor(self, obj):
        if obj.person:
            return str(obj.person)
        elif obj.organization:
            return str(obj.organization)
        else:
            return "none"


@admin.register(Preservation)
class PreservationAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "state", "pas_process_running")
    list_filter = ("state", "pas_process_running")
    search_fields = ("dataset__id",)
    readonly_fields = ("dataset",)


@admin.register(Temporal)
class TemporalAdmin(admin.ModelAdmin):
    list_display = ("id", "start_date", "end_date", "dataset", "provenance")
    list_filter = ("created", "modified", "start_date", "end_date")
    search_fields = ("dataset__id", "provenance__id")
    readonly_fields = ("dataset", "provenance")


@admin.register(Provenance)
class ProvenanceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "description")
    list_filter = ["created", "modified", "event_outcome", "lifecycle_event", "preservation_event"]
    autocomplete_fields = ["is_associated_with", "spatial"]
    search_fields = ("title__values", "dataset__id")
    readonly_fields = ("dataset",)


@admin.register(Spatial)
class SpatialAdmin(admin.ModelAdmin):
    list_display = ("id", "full_address", "geographic_name", "dataset")
    search_fields = ["dataset__id", "full_address", "geographic_name"]
    list_filter = ("created", "modified", "geographic_name")
    readonly_fields = ("reference", "dataset")


@admin.register(OtherIdentifier)
class OtherIdentifierAdmin(admin.ModelAdmin):
    list_display = ("notation",)
    list_filter = ("identifier_type", "created", "modified")


@admin.register(DatasetProject)
class DatasetProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "dataset")
    list_filter = ("created", "modified")
    search_fields = ["dataset__id", "title", "project_identifier"]
    autocomplete_fields = ["participating_organizations", "funding"]


@admin.register(LegacyDataset)
class LegacyDatasetAdmin(admin.ModelAdmin):
    fields = (
        "id",
        "created",
        "modified",
        "dataset_json",
        "contract_json",
        "v2_dataset_compatibility_diff",
        "last_successful_migration",
    )
    readonly_fields = (
        "id",
        "created",
        "modified",
        "v2_dataset_compatibility_diff",
        "last_successful_migration",
    )
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}


@admin.register(Contract)
class ContractAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "title",
        "quota",
    )
    list_filter = ("validity_end_date", "created", "modified")


@admin.register(DatasetLicense)
class LicenseAdmin(AbstractDatasetPropertyBaseAdmin):
    search_fields = ["title__values", "id", "description__values"]
    list_filter = ["reference"]


class EntityInline(admin.TabularInline):
    model = EntityRelation


@admin.register(Entity)
class EntityRelationAdmin(AbstractDatasetPropertyBaseAdmin):
    inlines = [EntityInline]
    list_filter = ("type", "created", "modified")
    autocomplete_fields = ("provenance",)


@admin.register(FileSet)
class FileSetAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(V2SyncStatus)
class V2SyncStatusAdmin(admin.ModelAdmin):
    readonly_fields = (
        "dataset",
        "sync_started",
        "sync_files_started",
        "sync_stopped",
        "duration",
        "action",
        "error",
    )
    list_display = (
        "dataset_id",
        "action",
        "sync_started",
        "sync_stopped",
        "duration",
        "status",
    )
    list_filter = ("sync_stopped",)
    actions = ["sync_to_v2"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not settings.METAX_V2_INTEGRATION_ENABLED:
            actions.pop("sync_to_v2")
        return actions

    @admin.action(description="Sync to V2", permissions=["change"])
    def sync_to_v2(self, request, queryset):
        V2SyncStatus.prefetch_datasets(queryset)
        for status in queryset:
            dataset: Dataset
            try:
                dataset = status.dataset
            except Dataset.DoesNotExist:
                if status.action == SyncAction.DELETE or status.action == SyncAction.FLUSH:
                    dataset = Dataset(id=status.dataset_id)
                else:
                    self.message_user(
                        request,
                        f"Dataset {status.dataset_id} not found",
                        messages.ERROR,
                    )
            run_task(sync_dataset_to_v2, dataset=dataset, action=status.action)
        self.message_user(
            request,
            f"{len(queryset)} datasets set to sync to V2",
            messages.SUCCESS,
        )
