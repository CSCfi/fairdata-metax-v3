from django.contrib import admin
from django.db.models import TextField
from django.forms import TextInput
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.
from apps.files.models import File, FileStorage


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
class FileStorageAdmin(AbstractDatasetPropertyBaseAdmin):
    list_display = ("id", "storage_service", "project_identifier")
    readonly_fields = ("storage_service", "file_count")

    @admin.display
    def file_count(self, obj):
        return obj.files.count()
