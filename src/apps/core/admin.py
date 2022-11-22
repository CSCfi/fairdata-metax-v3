from django.contrib import admin
from django.contrib.auth import get_user_model

# Register your models here.
from apps.core.models import (
    CatalogHomePage,
    DatasetPublisher,
    AccessRights,
    DataCatalog,
    CatalogRecord,
    Dataset,
    DataStorage,
    Distribution,
    File,
    Contract,
)


class AbstractDatasetPropertyBaseAdmin(admin.ModelAdmin):
    list_filter = ("created", "modified")
    exclude = ("is_removed", "removal_date")


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
class DataCatalogAdmin(AbstractDatasetPropertyBaseAdmin):
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


@admin.register(CatalogRecord)
class CatalogRecordAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "id",
        "data_catalog",
    )
    list_filter = ("created", "modified", "data_catalog")


@admin.register(Dataset)
class DatasetAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "title",
        "keyword",
        "access_rights",
        "is_deprecated",
    )
    list_filter = (
        "language",
        "keyword",
        "created",
        "modified",
        "is_removed",
        "issued",
        "is_deprecated",
    )


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
    list_filter = ["access_service"]


@admin.register(File)
class FileAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "file_name",
        "file_path",
    )
    list_filter = ["date_frozen"]


@admin.register(Contract)
class ContractAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = (
        "title",
        "quota",
    )
    list_filter = ("valid_until", "created", "modified")


admin.site.register(get_user_model())
