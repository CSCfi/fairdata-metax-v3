from copy import copy

from django.conf import settings
from django.contrib import admin
from django.db.models import TextField, F
from django.forms import ModelForm, TextInput
from django.utils.safestring import SafeString
from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin
from rest_framework.reverse import reverse

from apps.common.admin import AbstractDatasetPropertyBaseAdmin

# Register your models here.
from apps.files.helpers import replace_query_param
from apps.files.models import (
    BasicFileStorage,
    File,
    FileStorage,
    IDAFileStorage,
    ProjectFileStorage,
    FileCharacteristics,
)


@admin.register(FileCharacteristics)
class FileCharacteristicsAdmin(admin.ModelAdmin):
    list_display = ("id", "file_id")
    search_fields = ["id", "file_id"]
    readonly_fields = ["file_id"]

    def file_id(self, instance):
        return instance.file_id

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(file_id=F("file__id"))


@admin.register(File)
class FileAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = ("filename", "pathname", "csc_project", "storage")
    search_fields = ["id", "filename", "directory_path", "storage_identifier"]
    autocomplete_fields = ["pas_compatible_file", "characteristics"]

    def get_name(self, obj):
        return obj.author.name

    list_filter = [
        "frozen",
        "storage__csc_project",
    ]
    formfield_overrides = {
        TextField: {"widget": TextInput()},
    }


@admin.register(FileStorage)
class FileStorageAdmin(AbstractDatasetPropertyBaseAdmin, PolymorphicParentModelAdmin):
    list_display = ("id", "storage_service", "csc_project")

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


class FileStorageForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        model = self._meta.model
        for field in model.required_extra_fields:
            if field in self.fields:
                self.fields[field].required = True


class FileStorageProxyAdmin(AbstractDatasetPropertyBaseAdmin, PolymorphicChildModelAdmin):
    base_form = FileStorageForm

    readonly_fields = ("file_count", "project_root")

    @admin.display
    def file_count(self, obj: FileStorage):
        return obj.files.count()

    @admin.display
    def project_root(self, obj: FileStorage):
        url = reverse("directory-list")
        url = replace_query_param(url, param="storage_service", value=obj.storage_service)
        for field in obj.required_extra_fields:
            url = replace_query_param(url, param=field, value=getattr(obj, field))
        return SafeString(f'<a href="{url}">{url}</a>')

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
