from django.contrib import admin

# Register your models here.
from apps.core.models import (
    DatasetLanguage,
    CatalogHomePage,
    DatasetPublisher,
    DatasetLicense,
    AccessType,
    AccessRight,
    DataCatalog,
)


@admin.register(DatasetLanguage)
class DatasetLanguageAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(CatalogHomePage)
class CatalogHomePageAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(DatasetPublisher)
class DatasetPublisherAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(DatasetLicense)
class DatasetLicenseAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(AccessType)
class AccessTypeAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(AccessRight)
class AccessRightsAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")


@admin.register(DataCatalog)
class DataCatalogAdmin(admin.ModelAdmin):
    list_display = (
        "identifier",
        "dataset_versioning_enabled",
        "harvested",
        "research_dataset_schema",
    )
    list_filter = (
        "dataset_versioning_enabled",
        "harvested",
        "research_dataset_schema",
        "created",
        "modified",
    )
