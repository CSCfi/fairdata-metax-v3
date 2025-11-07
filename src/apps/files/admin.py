from typing import Optional

from django.conf import settings
from django.contrib import admin
from django.db.models import F, Q, TextField
from django.forms import ModelForm, TextInput
from django.utils.safestring import SafeString
from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin
from rest_framework.reverse import reverse

from apps.common.admin import AbstractDatasetPropertyBaseAdmin, CommonAdmin

# Register your models here.
from apps.common.helpers import is_valid_uuid
from apps.files.helpers import replace_query_param
from apps.files.models import (
    BasicFileStorage,
    File,
    FileCharacteristics,
    FileStorage,
    IDAFileStorage,
    ProjectFileStorage,
)


@admin.register(FileCharacteristics)
class FileCharacteristicsAdmin(CommonAdmin):
    list_display = ("id", "file_id")
    search_fields = ["id", "file_id"]
    readonly_fields = ["file_id"]

    def file_id(self, instance):
        return instance.file_id

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(file_id=F("file__id"))


class FileStorageFilter(admin.SimpleListFilter):
    title = "File Storage"
    parameter_name = "storage"

    def lookups(self, request, model_admin):
        choices = []
        services = (
            FileStorage.objects.order_by("storage_service")
            .values_list("storage_service", flat=True)
            .distinct()
        )
        keys = [f"{service}:*" for service in services]
        choices.extend((k, k) for k in keys)

        storages = (
            FileStorage.objects.order_by("storage_service", "csc_project")
            .values_list("storage_service", "csc_project")
            .distinct()
        )
        keys = [f"{service}:{project or '-'}" for service, project in storages]
        choices.extend((k, k) for k in keys)
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            service, project = value.split(":", 1)
            if project == "*":  # All projects in storage
                return queryset.filter(storage__storage_service=service)

            if project == "-":
                condition = Q(storage_service=service, csc_project__isnull=True)
            else:
                condition = Q(storage_service=service, csc_project=project)

            # Specific storage
            fs = FileStorage.objects.order_by().filter(condition).first()
            if not fs:
                return queryset.none()
            return queryset.filter(storage_id=fs.id)
        return queryset

    def choices(self, changelist):
        value = self.value()
        yield {
            "selected": value is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": "None",  # Replace "All" with "None", implemented in FileAdmin
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }


@admin.register(File)
class FileAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = ("storage_identifier", "pathname", "storage_service", "csc_project")
    autocomplete_fields = ["pas_compatible_file", "characteristics"]
    ordering = ["storage_id", "directory_path", "filename"]
    show_full_result_count = False # don't count total files
    exclude = []  # don't exclude "removed" timestamp
    show_facets = admin.ShowFacets.NEVER

    # Search fields have optimized implementation, see _get_search_filter
    search_fields = ["=id", "^storage_identifier", "^pathname"]

    def get_name(self, obj):
        return obj.author.name

    list_filter = ["frozen", FileStorageFilter]
    formfield_overrides = {
        TextField: {"widget": TextInput()},
    }

    def get_queryset(self, request):
        viewing_list = request.resolver_match.url_name.endswith("_changelist")
        if not viewing_list:
            # Allow soft deleted files in single file change view
            return File.all_objects.all()

        queryset = File.available_objects.all()

        # Display no files by default
        storage = request.GET.get("storage")
        if not storage:
            queryset = queryset.none()
        return queryset

    def _get_search_filter(self, field_name, search_term) -> Optional[Q]:
        """Return Q object for filtering a specific field."""
        if field_name == "^pathname":
            # All pathnames start with "/"
            if not search_term.startswith("/"):
                return

            q = Q(directory_path__startswith=search_term)
            if search_term.endswith("/"):
                return q  # Filename can't end with "/", search only directory_path

            # Search also with filename
            dir_path, filename = search_term.rsplit("/", 1)
            return q | Q(directory_path=f"{dir_path}/", filename__startswith=filename)
        elif field_name == "^storage_identifier":
            if search_term.startswith("/"):
                return  # Assume identifiers don't start with "/"
            return Q(storage_identifier__startswith=search_term)
        elif field_name == "=id":
            if not is_valid_uuid(search_term):
                return
            return Q(id__exact=search_term)
        raise NotImplementedError(f"Search for {field_name} not implemented")

    def get_search_results(self, request, queryset, search_term):
        """
        Return a tuple containing a queryset to implement the search
        and a boolean indicating if the results may contain duplicates.
        """

        # Optimized version that only supports specific File fields.
        # Unlike the default implementation, searches are case-sensitive.
        may_have_duplicates = False
        search_fields = self.get_search_fields(request)
        if not (search_fields and search_term):
            return queryset, may_have_duplicates

        filters = Q()
        for field_name in search_fields:
            q = self._get_search_filter(field_name=field_name, search_term=search_term)
            if q is not None:
                filters |= q
        queryset = queryset.filter(filters)
        return queryset, may_have_duplicates


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
