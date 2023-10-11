from django.contrib import admin
from django.contrib.auth import get_user_model
from simple_history.admin import SimpleHistoryAdmin

from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
from apps.core.models import (
    AccessRights,
    AccessRightsRestrictionGrounds,
    CatalogHomePage,
    CatalogRecord,
    Contract,
    DataCatalog,
    Dataset,
    DatasetActor,
    DatasetLicense,
    DatasetProject,
    DatasetPublisher,
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


@admin.register(AccessRightsRestrictionGrounds)
class AccessRightsRestrictionGroundsAdmin(admin.ModelAdmin):
    pass


@admin.register(DataCatalog)
class DataCatalogAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "id",
        "dataset_versioning_enabled",
        "harvested",
        "dataset_schema",
    )
    list_filter = (
        "dataset_versioning_enabled",
        "harvested",
        "dataset_schema",
        "created",
        "modified",
    )
    filter_horizontal = ("language",)


@admin.register(MetadataProvider)
class MetadataProviderAdmin(admin.ModelAdmin):
    list_display = ("user", "organization")


@admin.register(CatalogRecord)
class CatalogRecordAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "id",
        "data_catalog",
    )
    list_filter = ("created", "modified", "data_catalog")


@admin.register(Dataset)
class DatasetAdmin(AbstractDatasetPropertyBaseAdmin, SimpleHistoryAdmin):
    list_display = (
        "title",
        "keyword",
        "access_rights",
        "is_deprecated",
        "state",
    )
    list_filter = (
        "language",
        "keyword",
        "created",
        "modified",
        "is_removed",
        "issued",
        "is_deprecated",
        "state",
    )
    filter_horizontal = ("language", "theme", "field_of_science")
    list_select_related = ("access_rights", "data_catalog", "metadata_owner")


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
    list_display = ("name",)


@admin.register(LegacyDataset)
class LegacyDatasetAdmin(DatasetAdmin):
    fields = (
        "dataset_json",
        "contract_json",
        "title",
        "data_catalog",
        "access_rights",
        "keyword",
        "is_deprecated",
        "created",
        "modified",
        "issued",
    )
    readonly_fields = (
        "title",
        "data_catalog",
        "created",
        "modified",
        "issued",
        "access_rights",
        "keyword",
        "is_deprecated",
    )


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


@admin.register(FileSet)
class FileSetAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


admin.site.register(get_user_model())
