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
    CatalogRecord,
)


class AbstractDatasetPropertyBaseAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")
    exclude = ("is_removed", "removal_date")


@admin.register(DatasetLanguage)
class DatasetLanguageAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(CatalogHomePage)
class CatalogHomePageAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DatasetPublisher)
class DatasetPublisherAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DatasetLicense)
class DatasetLicenseAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(AccessType)
class AccessTypeAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(AccessRight)
class AccessRightsAdmin(AbstractDatasetPropertyBaseAdmin):
    pass


@admin.register(DataCatalog)
class DataCatalogAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "id",
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


@admin.register(CatalogRecord)
class CatalogRecordAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "id",
        "data_catalog",
    )
    list_filter = ("created", "modified", "data_catalog")
