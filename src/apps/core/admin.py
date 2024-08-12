import logging

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from simple_history.admin import SimpleHistoryAdmin

from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
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
    FileSet,
    LegacyDataset,
    MetadataProvider,
    OtherIdentifier,
    Provenance,
    Spatial,
    Temporal,
    Language,
    Theme,
    FieldOfScience,
    RestrictionGrounds,
    Funding,
)


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
        "harvested",
    )
    list_filter = (
        "dataset_versioning_enabled",
        "harvested",
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
    search_fields = ["pref_label__values"]
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
class FundingAdmin(admin.ModelAdmin):
    search_fields = ["funding_identifier"]
    list_filter = ("created", "modified")
    readonly_fields = ("funder",)


@admin.register(RestrictionGrounds)
class RestrictionGroundsAdmin(CoreRefDataAdminMixin, admin.ModelAdmin):
    pass


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
    autocomplete_fields = ['language', "theme", "field_of_science"]
    readonly_fields = (
        "dataset_versions",
        "other_identifiers",
        "last_modified_by",
        "access_rights",
        "draft_of",
    )
    list_select_related = ("access_rights", "data_catalog", "metadata_owner")
    search_fields = ["title__values", "keyword"]

    # inlines = [LanguageInline]

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
    search_fields = ("dataset__id", "person__name", "person__email", "roles", "organization__pref_label__values")

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
class LegacyDatasetAdmin(DatasetAdmin):
    fields = (
        "dataset_json",
        "contract_json",
        "title",
        "data_catalog",
        "access_rights",
        "keyword",
        "deprecated",
        "created",
        "modified",
        "issued",
        "v2_dataset_compatibility_diff",
    )
    readonly_fields = (
        "title",
        "data_catalog",
        "created",
        "modified",
        "issued",
        "access_rights",
        "keyword",
        "deprecated",
        # "v2_dataset_compatibility_diff",
    )
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}


@admin.register(Contract)
class ContractAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "title",
        "quota",
    )
    list_filter = ("valid_until", "created", "modified")


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


admin.site.register(get_user_model())
