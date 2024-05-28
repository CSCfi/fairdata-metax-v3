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
)


@admin.register(CatalogHomePage)
class CatalogHomePageAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DatasetPublisher)
class DatasetPublisherAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(AccessRights)
class AccessRightsAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


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
    filter_horizontal = ("language",)


@admin.register(MetadataProvider)
class MetadataProviderAdmin(admin.ModelAdmin):
    list_display = ("user", "organization")


@admin.register(Dataset)
class DatasetAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "title",
        "keyword",
        "access_rights",
        "deprecated",
        "state",
        "data_catalog",
        "created",
        "modified",
    )
    list_filter = (
        "language",
        "keyword",
        "created",
        "modified",
        "issued",
        "deprecated",
        "state",
    )
    filter_horizontal = ("language", "theme", "field_of_science")
    list_select_related = ("access_rights", "data_catalog", "metadata_owner")

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
    list_display = ("start_date", "end_date")


@admin.register(Provenance)
class ProvenanceAdmin(admin.ModelAdmin):
    list_display = ("title",)


@admin.register(Spatial)
class SpatialAdmin(admin.ModelAdmin):
    list_display = ("full_address", "geographic_name")


@admin.register(OtherIdentifier)
class OtherIdentifierAdmin(admin.ModelAdmin):
    list_display = ("notation", "dataset")


@admin.register(DatasetProject)
class DatasetProjectAdmin(admin.ModelAdmin):
    list_display = ("title",)


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
    list_filter = ("valid_until", "created", "modified")


@admin.register(DatasetLicense)
class LicenseAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


class EntityInline(admin.TabularInline):
    model = EntityRelation


@admin.register(Entity)
class EntityRelationAdmin(AbstractDatasetPropertyBaseAdmin):
    inlines = [EntityInline]


@admin.register(FileSet)
class FileSetAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


admin.site.register(get_user_model())
