from copy import copy

from django.conf import settings
from django.contrib import admin
from django.db.models import TextField
from django.forms import ModelForm, TextInput
from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.
from apps.files.models import (
    BasicFileStorage,
    File,
    FileStorage,
    IDAFileStorage,
    ProjectFileStorage,
)


class AbstractDatasetPropertyBaseAdmin(SimpleHistoryAdmin):
    list_filter = ("created", "modified")
    exclude = ("is_removed", "removal_date")


@admin.register(File)
class FileAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = ("file_name", "file_path", "project_identifier", "file_storage")

    def get_name(self, obj):
        return obj.author.name

    list_filter = [
        "date_frozen",
        "file_storage__project_identifier",
    ]
    formfield_overrides = {
        TextField: {"widget": TextInput()},
    }


@admin.register(FileStorage)
class FileStorageAdmin(AbstractDatasetPropertyBaseAdmin, PolymorphicParentModelAdmin):
    list_display = ("id", "storage_service", "project_identifier")
    readonly_fields = ("file_count",)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            readonly_fields = (*readonly_fields, "storage_service")
        return readonly_fields

    base_model = FileStorage
    child_models = (
        BasicFileStorage,
        ProjectFileStorage,
        IDAFileStorage,
    )

    @admin.display
    def file_count(self, obj):
        return obj.files.count()


class FileStorageForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        model = self._meta.model
        for field in model.required_extra_fields:
            self.fields[field].required = True


class FileStorageProxyAdmin(AbstractDatasetPropertyBaseAdmin, PolymorphicChildModelAdmin):
    base_form = FileStorageForm

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """List only storage services that match selected FileStorage class."""
        if db_field.name == "storage_service":
            storages = [
                storage
                for storage, classname in settings.STORAGE_SERVICE_FILE_STORAGES.items()
                if self.model.__name__ == classname
            ]
            kwargs["choices"] = ((storage, storage) for storage in storages)
        return super(AbstractDatasetPropertyBaseAdmin, self).formfield_for_choice_field(
            db_field, request, **kwargs
        )


@admin.register(BasicFileStorage)
class BasicFileStorageAdmin(FileStorageProxyAdmin):
    pass


@admin.register(ProjectFileStorage)
class BasicFileStorageAdmin(FileStorageProxyAdmin):
    pass


@admin.register(IDAFileStorage)
class IDAFileStorageAdmin(FileStorageProxyAdmin):
    pass
