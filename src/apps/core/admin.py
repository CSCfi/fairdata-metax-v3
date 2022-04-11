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
    DataStorage,
    Distribution,
    File,
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

@admin.register(DataStorage)
class DataStorageAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "id",
        "endpoint_url",
        "endpoint_description",
    )
    list_filter = ("created", "modified")

@admin.register(Distribution)
class DistributionAdmin(AbstractDatasetPropertyBaseAdmin):
    pass

@admin.register(File)
class FileAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "file_name",
        "file_path",
    )
    list_filter = ("file_storage", "date_frozen")
